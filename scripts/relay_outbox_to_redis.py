#!/usr/bin/env python3
"""
Relay service that publishes outbox events to Redis Streams.
Runs as a separate process for fault isolation.
"""
import os
import sys
import time
import json
import logging
import psycopg2
import redis
from typing import List, Dict, Optional
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OutboxRelay:
    """Relay events from Postgres outbox to Redis Streams"""
    
    def __init__(
        self, 
        db_url: str,
        redis_url: str,
        stream_key: str = 'events',
        dlq_key: str = 'events:dlq',
        batch_size: int = 100,
        poll_interval_ms: int = 300,
        retry_limit: int = 5
    ):
        self.db_conn = psycopg2.connect(db_url)
        self.db_conn.autocommit = False
        
        if not redis_url:
            try:
                from scripts.lib.redis_utils import build_redis_url
                redis_url = build_redis_url(role='publisher')
            except Exception:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=5,
        )
        self.stream_key = stream_key
        self.dlq_key = dlq_key
        self.batch_size = batch_size
        self.poll_interval_ms = poll_interval_ms
        self.retry_limit = retry_limit
        
        self._ensure_stream_exists()
        logger.info(f"✅ Relay initialized: stream={stream_key}, batch={batch_size}")
    
    def _ensure_stream_exists(self):
        """Ensure the stream exists (creates empty stream if not)"""
        try:
            # Try to get stream info
            self.redis_client.xinfo_stream(self.stream_key)
        except redis.ResponseError:
            # Stream doesn't exist, create with dummy entry then delete
            dummy_id = self.redis_client.xadd(self.stream_key, {'init': 'true'})
            self.redis_client.xdel(self.stream_key, dummy_id)
            logger.info(f"Created stream: {self.stream_key}")
    
    def fetch_unpublished_events(self) -> List[Dict]:
        """Fetch batch of unpublished events from outbox"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, type, chain_id, block_number, tx_hash, log_index,
                       auction_address, round_id, from_token, want_token,
                       timestamp, payload_json, uniq, ver, retries
                FROM outbox_events
                WHERE published_at IS NULL
                ORDER BY id
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            """, (self.batch_size,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def publish_to_stream(self, event: Dict) -> bool:
        """Publish single event to Redis Stream"""
        try:
            # Normalize tx hash to include 0x prefix
            txh = event.get('tx_hash')
            if isinstance(txh, str) and not txh.startswith('0x'):
                txh = '0x' + txh
            # Prepare fields for XADD (all values must be strings)
            fields = {
                'type': event['type'],
                'chain_id': str(event['chain_id']),
                'block_number': str(event['block_number']),
                'tx_hash': txh if txh is not None else '',
                'log_index': str(event['log_index']),
                'auction_address': event['auction_address'] or '',
                'timestamp': str(event['timestamp']),
                'uniq': event['uniq'],
                'ver': str(event['ver']),
                'payload_json': json.dumps(event['payload_json'])
            }
            
            # Add optional fields
            if event.get('round_id'):
                fields['round_id'] = str(event['round_id'])
            if event.get('from_token'):
                fields['from_token'] = event['from_token']
            if event.get('want_token'):
                fields['want_token'] = event['want_token']
            
            # Publish with approximate max length for auto-trimming
            message_id = self.redis_client.xadd(
                self.stream_key,
                fields,
                maxlen=100000,
                approximate=True
            )
            
            logger.debug(f"Published event {event['uniq']} as {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event['id']}: {e}")
            return False
    
    def mark_published(self, event_id: int):
        """Mark event as published in outbox"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                UPDATE outbox_events
                SET published_at = NOW()
                WHERE id = %s
            """, (event_id,))
    
    def increment_retry(self, event_id: int, error: str):
        """Increment retry count and record error"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                UPDATE outbox_events
                SET retries = retries + 1,
                    last_error = %s
                WHERE id = %s
            """, (error[:500], event_id))  # Truncate error message
    
    def move_to_dlq(self, event: Dict):
        """Move failed event to dead letter queue"""
        try:
            fields = {
                'original_event': json.dumps(event),
                'failure_time': str(int(time.time())),
                'retries': str(event['retries']),
                'last_error': event.get('last_error', 'Unknown')
            }
            
            self.redis_client.xadd(self.dlq_key, fields)
            logger.warning(f"Moved event {event['id']} to DLQ after {event['retries']} retries")
            
            # Mark as published to prevent blocking
            self.mark_published(event['id'])
            
        except Exception as e:
            logger.error(f"Failed to move event {event['id']} to DLQ: {e}")
    
    def process_batch(self):
        """Process a batch of events"""
        events = self.fetch_unpublished_events()
        
        if not events:
            return 0
        
        processed = 0
        for event in events:
            try:
                # Check retry limit
                if event['retries'] >= self.retry_limit:
                    self.move_to_dlq(event)
                    processed += 1
                    continue
                
                # Attempt to publish
                if self.publish_to_stream(event):
                    self.mark_published(event['id'])
                    processed += 1
                else:
                    self.increment_retry(event['id'], "Redis publish failed")
                
                self.db_conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing event {event['id']}: {e}")
                self.db_conn.rollback()
                self.increment_retry(event['id'], str(e))
                self.db_conn.commit()
        
        if processed > 0:
            logger.info(f"📤 Relayed {processed}/{len(events)} events to Redis")
        
        return processed
    
    def run(self):
        """Main relay loop"""
        logger.info("🚀 Starting Outbox Relay Service")
        logger.info(f"📊 Config: batch={self.batch_size}, poll={self.poll_interval_ms}ms, retry_limit={self.retry_limit}")
        
        consecutive_empty = 0
        
        while True:
            try:
                processed = self.process_batch()
                
                if processed == 0:
                    consecutive_empty += 1
                    # Back off when queue is empty
                    sleep_ms = min(self.poll_interval_ms * consecutive_empty, 5000)
                else:
                    consecutive_empty = 0
                    sleep_ms = self.poll_interval_ms
                
                time.sleep(sleep_ms / 1000.0)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping relay service...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in relay loop: {e}")
                time.sleep(1)

def main():
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Outbox to Redis Relay Service')
    parser.add_argument('--batch-size', type=int, default=100)
    parser.add_argument('--poll-interval', type=int, default=300)
    parser.add_argument('--retry-limit', type=int, default=5)
    
    args = parser.parse_args()
    
    # Get configuration from environment
    app_mode = os.getenv('APP_MODE', 'dev')
    db_url = os.getenv(f'{app_mode.upper()}_DATABASE_URL')
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    if not db_url:
        logger.error("Database URL not configured")
        sys.exit(1)
    
    relay = OutboxRelay(
        db_url=db_url,
        redis_url=redis_url,
        batch_size=args.batch_size,
        poll_interval_ms=args.poll_interval,
        retry_limit=args.retry_limit
    )
    
    relay.run()

if __name__ == '__main__':
    main()
