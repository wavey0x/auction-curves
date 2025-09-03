# Redis Streams Implementation Specification

## Executive Summary

This specification details the implementation of Redis Streams as a reliable pub/sub layer for the auction monitoring system, using the **Transactional Outbox Pattern** to ensure data consistency and message reliability.

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│  Blockchain │────▶│         INDEXER                    │────▶│   Postgres  │
└─────────────┘     │  1. Process events                │     │   (truth)   │
                    │  2. Write domain + outbox (1 tx)   │     └─────────────┘
                    └──────────────────────────────────┘              │
                                                                       ▼
                    ┌──────────────────────────────────┐     ┌─────────────┐
                    │         RELAY SERVICE             │◀────│   Outbox    │
                    │  Poll outbox → Publish to Redis  │     │   Table     │
                    └──────────────────────────────────┘     └─────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │       REDIS STREAMS              │
                    │         events stream            │
                    └──────────────────────────────────┘
                                      │
                    ┌─────────────────┴────────────────┐
                    ▼                 ▼                ▼
            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
            │  Telegram   │  │   Pricing   │  │   Web UI    │
            │  Consumer   │  │  Consumer   │  │  Notifier   │
            └─────────────┘  └─────────────┘  └─────────────┘
```

## Implementation Files

### 1. Database Migration: `data/postgres/migrations/009_add_outbox_events.sql`

```sql
-- Create outbox table for reliable event publishing
CREATE TABLE IF NOT EXISTS outbox_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Event metadata
    type VARCHAR(50) NOT NULL,
    chain_id INTEGER NOT NULL,
    block_number BIGINT NOT NULL,
    tx_hash VARCHAR(100) NOT NULL,
    log_index INTEGER NOT NULL,
    
    -- Event data
    auction_address VARCHAR(100),
    round_id INTEGER,
    from_token VARCHAR(100),
    want_token VARCHAR(100),
    timestamp BIGINT NOT NULL,
    
    -- Payload for event-specific data
    payload_json JSONB NOT NULL DEFAULT '{}',
    
    -- Idempotency and versioning
    uniq VARCHAR(200) NOT NULL,
    ver INTEGER NOT NULL DEFAULT 1,
    
    -- Publishing status
    published_at TIMESTAMPTZ,
    retries INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT outbox_events_uniq_key UNIQUE (uniq)
);

-- Indexes for efficient polling
CREATE INDEX idx_outbox_unpublished ON outbox_events (id) 
    WHERE published_at IS NULL;
CREATE INDEX idx_outbox_chain_block ON outbox_events (chain_id, block_number);
CREATE INDEX idx_outbox_created ON outbox_events (created_at);

-- For monitoring stuck events
CREATE INDEX idx_outbox_retries ON outbox_events (retries) 
    WHERE published_at IS NULL AND retries > 3;
```

### 2. Indexer Integration: `indexer/event_publisher.py`

```python
"""
Event publishing helper for the indexer.
Inserts events into the outbox table within the same transaction.
"""
import json
from typing import Dict, Any, Optional
from decimal import Decimal

class EventPublisher:
    """Helper class to publish events to the outbox table"""
    
    EVENT_TYPES = {
        'AUCTION_DEPLOYED': 'deploy',
        'ROUND_KICKED': 'kick', 
        'TAKE_EXECUTED': 'take',
    }
    
    @staticmethod
    def create_uniq_key(chain_id: int, tx_hash: str, log_index: int) -> str:
        """Create unique idempotency key for an event"""
        return f"{chain_id}:{tx_hash.lower()}:{log_index}"
    
    @staticmethod
    def decimal_to_str(obj):
        """Convert Decimal to string for JSON serialization"""
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError
    
    def insert_outbox_event(
        self,
        cursor,
        event_type: str,
        chain_id: int,
        block_number: int,
        tx_hash: str,
        log_index: int,
        auction_address: str,
        timestamp: int,
        payload: Dict[str, Any],
        round_id: Optional[int] = None,
        from_token: Optional[str] = None,
        want_token: Optional[str] = None
    ) -> None:
        """
        Insert event into outbox table.
        Should be called within the same transaction as domain inserts.
        """
        uniq = self.create_uniq_key(chain_id, tx_hash, log_index)
        
        # Ensure payload is JSON-serializable
        payload_json = json.dumps(payload, default=self.decimal_to_str)
        
        cursor.execute("""
            INSERT INTO outbox_events (
                type, chain_id, block_number, tx_hash, log_index,
                auction_address, round_id, from_token, want_token,
                timestamp, payload_json, uniq, ver
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            ON CONFLICT (uniq) DO NOTHING
        """, (
            event_type, chain_id, block_number, tx_hash, log_index,
            auction_address, round_id, from_token, want_token,
            timestamp, payload_json, uniq
        ))

# Usage in indexer.py:
# In process_deployed_event:
publisher = EventPublisher()
publisher.insert_outbox_event(
    cursor=cursor,
    event_type='deploy',
    chain_id=self.chain_id,
    block_number=event['blockNumber'],
    tx_hash=event['transactionHash'].hex(),
    log_index=event['logIndex'],
    auction_address=auction_address,
    timestamp=block_timestamp,
    payload={
        'deployer': deployer,
        'version': version,
        'from_tokens': from_tokens,
        'want_token': want_token
    }
)
```

### 3. Relay Service: `scripts/relay_outbox_to_redis.py`

```python
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
        
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
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
            # Prepare fields for XADD (all values must be strings)
            fields = {
                'type': event['type'],
                'chain_id': str(event['chain_id']),
                'block_number': str(event['block_number']),
                'tx_hash': event['tx_hash'],
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
```

### 4. Sample Consumer: `scripts/consumers/telegram_consumer.py`

```python
#!/usr/bin/env python3
"""
Telegram bot consumer for Redis Streams events
"""
import os
import sys
import json
import time
import logging
import redis
from typing import Dict, List

logger = logging.getLogger(__name__)

class TelegramConsumer:
    """Consumer that sends auction events to Telegram"""
    
    def __init__(self, redis_url: str, stream_key: str = 'events'):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.stream_key = stream_key
        self.consumer_group = 'telegram'
        self.consumer_name = f'telegram-{os.getpid()}'
        
        self._ensure_consumer_group()
    
    def _ensure_consumer_group(self):
        """Create consumer group if it doesn't exist"""
        try:
            self.redis_client.xgroup_create(
                self.stream_key, 
                self.consumer_group, 
                id='0'
            )
            logger.info(f"Created consumer group: {self.consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    
    def process_event(self, event: Dict) -> bool:
        """Process single event - format and send to Telegram"""
        try:
            event_type = event.get('type')
            
            if event_type == 'kick':
                message = self._format_kick_event(event)
            elif event_type == 'take':
                message = self._format_take_event(event)
            elif event_type == 'deploy':
                message = self._format_deploy_event(event)
            else:
                logger.debug(f"Ignoring event type: {event_type}")
                return True
            
            # TODO: Actually send to Telegram
            logger.info(f"📱 Would send to Telegram: {message[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            return False
    
    def _format_kick_event(self, event: Dict) -> str:
        """Format kick event for Telegram"""
        payload = json.loads(event.get('payload_json', '{}'))
        return (
            f"🚀 New Auction Round!\n"
            f"Round #{event.get('round_id', 'N/A')}\n"
            f"Available: {payload.get('initial_available', 'N/A')}\n"
        )
    
    def _format_take_event(self, event: Dict) -> str:
        """Format take event for Telegram"""
        payload = json.loads(event.get('payload_json', '{}'))
        return (
            f"💰 Auction Take!\n"
            f"Amount: {payload.get('amount_taken', 'N/A')}\n"
            f"Price: ${payload.get('price', 'N/A')}\n"
        )
    
    def _format_deploy_event(self, event: Dict) -> str:
        """Format deploy event for Telegram"""
        return f"🏭 New Auction Deployed!\nAddress: {event.get('auction_address', 'N/A')}\n"
    
    def run(self):
        """Main consumer loop"""
        logger.info(f"🚀 Starting Telegram Consumer as {self.consumer_name}")
        
        while True:
            try:
                # Read with consumer group
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: '>'},
                    count=10,
                    block=5000  # Block for 5 seconds
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, data in stream_messages:
                        # Process event
                        if self.process_event(data):
                            # Acknowledge successful processing
                            self.redis_client.xack(
                                self.stream_key,
                                self.consumer_group,
                                message_id
                            )
                        else:
                            # Will be retried later via pending list
                            logger.warning(f"Failed to process {message_id}, will retry")
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping consumer...")
                break
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                time.sleep(1)

def main():
    logging.basicConfig(level=logging.INFO)
    
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    consumer = TelegramConsumer(redis_url)
    consumer.run()

if __name__ == '__main__':
    main()
```

### 5. Docker Compose Update: Add to `docker-compose.yml`

```yaml
  redis:
    image: redis:7-alpine
    container_name: auction_redis
    command: redis-server --appendonly yes --save "" --maxmemory 256mb --maxmemory-policy noeviction
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    restart: unless-stopped
```

### 6. Environment Configuration: Add to `.env.example`

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_STREAM_KEY=events
REDIS_DLQ_KEY=events:dlq
REDIS_CONSUMER_GROUPS=telegram,pricing,ui

# Relay Configuration  
RELAY_BATCH_SIZE=100
RELAY_POLL_INTERVAL_MS=300
RELAY_RETRY_LIMIT=5
```

### 7. Dev Script Update: Modify `dev.sh`

Add Redis and relay to the startup sequence:

```bash
# Start Redis
echo "Starting Redis..."
docker-compose up -d redis

# Wait for Redis
wait_for_service "Redis" "redis-cli ping" 10

# Start relay service (after database is ready)
start_service "relay" "Outbox Relay" \
    "python3 scripts/relay_outbox_to_redis.py" \
    "Starting Outbox Relay Service"
```

## Testing Strategy

### Unit Tests

1. **Event Publisher Tests** (`tests/test_event_publisher.py`)
   - Test unique key generation
   - Test JSON serialization
   - Test idempotent inserts

2. **Relay Tests** (`tests/test_relay.py`)
   - Test batch fetching
   - Test Redis publishing
   - Test retry logic
   - Test DLQ handling

### Integration Tests

1. **End-to-End Flow** (`tests/test_e2e_flow.py`)
   - Insert event via indexer
   - Verify outbox entry created
   - Run relay cycle
   - Verify Redis stream entry
   - Consume with test consumer
   - Verify acknowledgment

### Load Tests

```python
# tests/load_test_relay.py
# Generate 10,000 outbox events
# Measure relay throughput
# Monitor Redis memory usage
# Check consumer lag
```

## Monitoring & Observability

### Key Metrics

1. **Relay Health**
   ```sql
   -- Outbox backlog
   SELECT COUNT(*) as backlog
   FROM outbox_events
   WHERE published_at IS NULL;
   
   -- Stuck events
   SELECT COUNT(*) as stuck
   FROM outbox_events
   WHERE published_at IS NULL AND retries > 3;
   ```

2. **Redis Stream Health**
   ```bash
   # Stream length
   redis-cli XLEN events
   
   # Consumer lag
   redis-cli XPENDING events telegram
   ```

3. **Consumer Health**
   - Messages processed per minute
   - Processing latency
   - Error rate

### Alerting Rules

- Outbox backlog > 1000 events
- Any event with retries > 5
- Consumer lag > 500 messages
- Redis memory > 80% of max

## Migration Plan

### Phase 1: Infrastructure (Day 1)
1. Deploy Redis container
2. Run outbox table migration
3. Deploy relay service (inactive)
4. Verify connectivity

### Phase 2: Publishing (Day 2)
1. Update indexer with EventPublisher
2. Start with deploy events only
3. Monitor outbox population
4. Enable relay service
5. Verify Redis stream population

### Phase 3: First Consumer (Day 3)
1. Deploy Telegram consumer
2. Test with manual events
3. Enable for production events
4. Monitor end-to-end flow

### Phase 4: Additional Consumers (Day 4-5)
1. Add pricing service consumer
2. Add UI notifier
3. Performance tuning

### Rollback Procedure

Each phase can be rolled back independently:

1. **Disable relay**: Stop relay service, events accumulate in outbox
2. **Disable publishing**: Remove EventPublisher calls from indexer
3. **Remove consumers**: Stop consumer services
4. **Clean up**: Truncate outbox table, flush Redis

## Performance Considerations

### Expected Throughput
- Indexer: ~100 events/minute peak
- Relay: 1000+ events/second capability
- Redis: 10,000+ messages/second
- Consumers: Varies by processing complexity

### Resource Requirements
- Redis: 256MB RAM (holds ~100k events)
- Relay: Minimal (< 50MB RAM)
- Consumers: Depends on business logic

### Tuning Parameters
- Relay batch size: Start with 100, increase if lag builds
- Poll interval: 300ms default, reduce for lower latency
- Redis maxlen: 100k events (~24 hours retention)
- Consumer batch size: 10-50 depending on processing time

## Operational Runbook

### Common Issues

1. **High outbox backlog**
   - Check relay logs for errors
   - Verify Redis connectivity
   - Increase batch size temporarily

2. **Consumer lag**
   - Scale consumer instances
   - Check for processing errors
   - Review consumer batch size

3. **Redis memory pressure**
   - Reduce stream maxlen
   - Add time-based trimming
   - Scale Redis instance

### Maintenance Tasks

- Weekly: Review DLQ for patterns
- Monthly: Analyze event volume trends
- Quarterly: Load test with 10x volume

## Summary

This implementation provides:
1. **Reliability**: Transactional outbox ensures no event loss
2. **Scalability**: Redis Streams handle high throughput
3. **Flexibility**: Easy to add new consumers
4. **Observability**: Clear metrics and monitoring
5. **Simplicity**: Minimal code changes to existing system

The system can be deployed incrementally with rollback capability at each phase.