#!/usr/bin/env python3
"""
Odos Price Service
Polls for recent takes and fetches current token prices from Odos API
"""

import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
import requests
import argparse
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OdosPriceService:
    """Price service using Odos API to fetch current token prices"""
    
    def __init__(self, poll_interval: int = 6, recency_blocks: int = 40, once: bool = False):
        self.db_conn = None
        self.poll_interval = max(1, int(poll_interval))
        self.recency_blocks = recency_blocks
        self.once = once
        self.api_key = os.getenv('ODOS_API_KEY')
        self.base_url = "https://api.odos.xyz/pricing/token"
        self.chain_names = {
            1: "1",  # Mainnet
            137: "137",  # Polygon
            42161: "42161",  # Arbitrum
            10: "10",  # Optimism
            8453: "8453",  # Base
        }
        self.processed_takes = set()  # Track processed take IDs in this session
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            # Use the same database URL as other services
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            if app_mode == 'dev':
                db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5432/auction_dev')
            elif app_mode == 'prod':
                db_url = os.getenv('PROD_DATABASE_URL')
            else:
                logger.error(f"Unsupported APP_MODE for price service: {app_mode}")
                sys.exit(1)
                
            if not db_url:
                logger.error("No database URL configured")
                sys.exit(1)
                
            self.db_conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
            self.db_conn.autocommit = True
            logger.info("✅ Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def get_recent_takes(self) -> List[Dict]:
        """Get takes from the last N blocks that haven't been processed yet"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get recent takes (within recency_blocks of the latest block)
                cursor.execute("""
                    WITH latest_blocks AS (
                        SELECT chain_id, MAX(block_number) as max_block
                        FROM takes
                        GROUP BY chain_id
                    )
                    SELECT t.*, lb.max_block
                    FROM takes t
                    JOIN latest_blocks lb ON t.chain_id = lb.chain_id
                    WHERE t.block_number > lb.max_block - %s
                      AND t.chain_id IN %s
                    ORDER BY t.timestamp DESC
                    LIMIT 100
                """, (self.recency_blocks, tuple(self.chain_names.keys())))
                
                takes = cursor.fetchall()
                
                # Filter out already processed takes
                new_takes = [t for t in takes if t['take_id'] not in self.processed_takes]
                
                if new_takes:
                    logger.info(f"[ODOS] Found {len(new_takes)} recent unprocessed takes (< {self.recency_blocks} blocks old)")
                
                return new_takes
                
        except Exception as e:
            logger.error(f"Failed to get recent takes: {e}")
            return []
    
    def fetch_token_price(self, token_address: str, chain_id: int) -> Optional[Decimal]:
        """Fetch current price for a token from Odos API"""
        if chain_id not in self.chain_names:
            logger.debug(f"Chain {chain_id} not supported by Odos")
            return None
            
        try:
            # Odos API endpoint
            url = f"{self.base_url}/{self.chain_names[chain_id]}/{token_address}"
            
            headers = {}
            if self.api_key:
                headers['X-API-KEY'] = self.api_key
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse response - adjust based on actual Odos API format
                if 'tokenPrices' in data and token_address.lower() in data['tokenPrices']:
                    price_data = data['tokenPrices'][token_address.lower()]
                    price = price_data.get('price')
                    if price:
                        return Decimal(str(price))
                elif 'price' in data:
                    return Decimal(str(data['price']))
                    
            elif response.status_code == 429:
                logger.warning(f"Rate limit hit for Odos API")
                time.sleep(1)  # Brief pause on rate limit
            else:
                logger.debug(f"Odos API returned status {response.status_code} for {token_address}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Odos API request failed for {token_address}: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Odos response for {token_address}: {e}")
            
        return None
    
    def store_price(self, chain_id: int, token_address: str, price_usd: Decimal, block_number: int) -> None:
        """Store token price in database"""
        try:
            with self.db_conn.cursor() as cursor:
                # Store with current timestamp since Odos provides current prices
                cursor.execute("""
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address, 
                        price_usd, timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, 'odos', NOW())
                """, (
                    chain_id, 
                    block_number,  # Store the block from the take for reference
                    token_address, 
                    price_usd,
                    int(time.time())  # Current timestamp
                ))
                
                if cursor.rowcount > 0:
                    logger.info(f"[ODOS] 💰 Stored price: {token_address[:6]}..{token_address[-4:]} = ${price_usd:.4f}")
                    
        except Exception as e:
            logger.error(f"Failed to store price for {token_address}: {e}")
    
    def process_take(self, take: Dict) -> None:
        """Process a single take and fetch prices for its tokens"""
        try:
            take_id = take['take_id']
            chain_id = take['chain_id']
            from_token = take['from_token']
            want_token = take['to_token']  # Column name is 'to_token' in database
            block_number = take['block_number']
            
            logger.debug(f"Processing take {take_id[:8]}... on chain {chain_id}")
            
            # Fetch prices for both tokens
            tokens_to_price = [(from_token, 'from'), (want_token, 'want')]
            prices_stored = 0
            
            for token_address, token_type in tokens_to_price:
                price = self.fetch_token_price(token_address, chain_id)
                
                if price is not None:
                    self.store_price(chain_id, token_address, price, block_number)
                    prices_stored += 1
                else:
                    logger.debug(f"No price available for {token_type} token {token_address[:6]}...")
            
            # Mark as processed
            self.processed_takes.add(take_id)
            
            if prices_stored > 0:
                logger.info(f"[ODOS] ✅ Processed take {take_id[:8]}...: stored {prices_stored} prices")
                
        except Exception as e:
            logger.error(f"Failed to process take {take.get('take_id', 'unknown')}: {e}")
    
    def run_polling_loop(self) -> None:
        """Main polling loop"""
        logger.info("🚀 Starting Odos Price Service")
        logger.info(f"📊 Settings: poll_interval={self.poll_interval}s, recency_blocks={self.recency_blocks}")
        
        if self.api_key:
            logger.info("🔑 Odos API key configured")
        else:
            logger.warning("⚠️  No Odos API key configured - may hit rate limits")
        
        while True:
            try:
                # Get recent takes
                recent_takes = self.get_recent_takes()
                
                if recent_takes:
                    for take in recent_takes:
                        self.process_take(take)
                        # Small delay between takes to avoid rate limits
                        time.sleep(0.1)
                else:
                    logger.debug(f"[ODOS] No new recent takes found")
                
                if self.once:
                    logger.info("✅ Single cycle completed (--once mode)")
                    break
                
                # Wait before next poll
                logger.debug(f"[ODOS] Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping Odos price service...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                if not self.once:
                    time.sleep(self.poll_interval)
                else:
                    break

def main():
    parser = argparse.ArgumentParser(description='Odos Price Service')
    parser.add_argument('--poll-interval', type=int, default=6, 
                       help='Poll interval in seconds (default: 6)')
    parser.add_argument('--recency-blocks', type=int, default=40,
                       help='How recent takes must be in blocks (default: 40)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    service = OdosPriceService(
        poll_interval=args.poll_interval,
        recency_blocks=args.recency_blocks,
        once=args.once
    )
    
    try:
        service.run_polling_loop()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()