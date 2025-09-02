#!/usr/bin/env python3
"""
ypricemagic Price Service
Long-running service that polls the price_requests queue and fetches USD prices using ypricemagic
"""

import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
import traceback
import decimal
import argparse
from decimal import Decimal
from typing import Optional, Tuple
from datetime import datetime
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

class YPriceMagicService:
    """Price service using ypricemagic to fetch historical token prices"""
    
    def __init__(self, network_name: str = "electro", poll_interval: int = 5, prioritize_failed: bool = False, once: bool = False):
        self.db_conn = None
        self.brownie_network = network_name
        self.poll_interval = max(1, int(poll_interval))
        self.prioritize_failed = prioritize_failed
        self.once = once
        self.block_timestamp_cache = {}  # Cache for block number -> timestamp
        self._init_database()
        
    def _checksum_address(self, address: str) -> str:
        """Convert address to proper checksum format"""
        try:
            from eth_utils import to_checksum_address
            return to_checksum_address(address)
        except ImportError:
            from brownie import web3
            return web3.toChecksumAddress(address)
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            # Use the same database URL as the indexer
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            if app_mode == 'dev':
                db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5433/auction_dev')
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
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def _init_brownie_network(self) -> None:
        """Initialize Brownie network connection"""
        try:
            from brownie import network, chain, web3
            
            logger.info("🌐 Initializing Brownie network connection...")
            
            # Connect to requested network
            target = self.brownie_network or 'development'
            if not network.is_connected():
                logger.info(f"Connecting to '{target}' network...")
                network.connect(target)
                logger.info(f"✅ Connected to Brownie network: {network.show_active()}")
            else:
                logger.info(f"✅ Already connected to Brownie network: {network.show_active()}")
            
            # Log chain information
            logger.info(f"📊 Chain info: height={chain.height}, id={chain.id}")
            logger.debug(f"Chain methods available: {[method for method in dir(chain) if not method.startswith('_')]}")
            
            # Test web3 connection
            try:
                latest_block = web3.eth.get_block('latest')
                logger.info(f"🌐 Web3 connection test: latest block = {latest_block['number']}")
            except Exception as web3_error:
                logger.warning(f"⚠️  Web3 connection test failed: {web3_error}")
                
            # Import ypricemagic after network is connected
            try:
                logger.info("📦 Importing ypricemagic...")
                from y import magic
                self.magic = magic
                logger.info("✅ ypricemagic imported successfully")
                
                # Test a simple call to see if ypricemagic is working
                logger.info("🧪 Testing ypricemagic functionality...")
                # Test with WETH address and a recent block (non-blocking)
                # test_price = magic.get_price("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", block=20000000, sync=False)
                # logger.debug(f"ypricemagic test call initiated (async)")
                
            except ImportError as e:
                logger.error(f"❌ Failed to import ypricemagic: {e}")
                logger.error("Install with: pip install ypricemagic")
                sys.exit(1)
            except Exception as magic_error:
                logger.error(f"❌ ypricemagic test failed: {magic_error}")
                logger.warning("Continuing anyway - may work for actual requests...")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Brownie network: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            sys.exit(1)
    
    def get_pending_requests(self) -> list:
        """Fetch pending price requests from database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, chain_id, block_number, token_address, 
                           request_type, auction_address, round_id, retry_count, txn_timestamp
                    FROM price_requests 
                    WHERE status = 'pending' 
                      AND retry_count < 3
                    ORDER BY created_at ASC 
                    LIMIT 50
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch pending requests: {e}")
            return []
    
    def get_total_pending_count(self) -> int:
        """Get total count of pending requests for backlog reporting"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM price_requests 
                    WHERE status = 'pending' 
                      AND retry_count < 3
                """)
                return cursor.fetchone()['count']
        except Exception as e:
            logger.error(f"Failed to get pending requests count: {e}")
            return 0

    def get_failed_requests(self, limit: int = 50) -> list:
        """Fetch failed price requests eligible for retry"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, chain_id, block_number, token_address,
                           request_type, auction_address, round_id, retry_count, txn_timestamp
                    FROM price_requests
                    WHERE status = 'failed' AND retry_count < 3
                    ORDER BY processed_at ASC NULLS FIRST, id ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch failed requests: {e}")
            return []
    
    def mark_request_processing(self, request_id: int) -> None:
        """Mark request as being processed"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'processing', processed_at = NOW()
                    WHERE id = %s
                """, (request_id,))
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as processing: {e}")
    
    def get_token_symbol(self, chain_id: int, token_address: str) -> Optional[str]:
        """Get token symbol for better debugging logs"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT symbol FROM tokens 
                    WHERE chain_id = %s 
                      AND LOWER(address) = LOWER(%s)
                    LIMIT 1
                """, (chain_id, token_address))
                result = cursor.fetchone()
                return result['symbol'] if result else None
        except Exception as e:
            logger.debug(f"Failed to get token symbol for {token_address}: {e}")
            return None
    
    def fetch_token_price(self, token_address: str, block_number: int) -> Tuple[Optional[Decimal], Optional[int], Optional[str]]:
        """
        Fetch token price using ypricemagic at specific block
        Returns: (price_usd, timestamp, error_msg) or (None, None, error_msg) if failed
        """
        try:
            from brownie import chain, web3
            
            # Use ypricemagic to get price
            try:
                price = self.magic.get_price(token_address, block=block_number, sync=True)
            except Exception as ypm_error:
                return None, None, f"ypricemagic error: {str(ypm_error)}"
            
            if price is None or price <= 0:
                return None, None, f"ypricemagic returned invalid price: {price}"
            
            # Get block timestamp with caching
            if block_number in self.block_timestamp_cache:
                timestamp = self.block_timestamp_cache[block_number]
            else:
                try:
                    # Try using brownie's web3 instance
                    block_info = web3.eth.get_block(block_number)
                    timestamp = block_info['timestamp']
                    
                    # Cache the timestamp, implement simple LRU by size limit
                    if len(self.block_timestamp_cache) >= 1000:
                        # Remove oldest entry (FIFO)
                        oldest_key = next(iter(self.block_timestamp_cache))
                        del self.block_timestamp_cache[oldest_key]
                    
                    self.block_timestamp_cache[block_number] = timestamp
                    
                except Exception as block_error:
                    # Fallback: try chain methods
                    try:
                        # Try different chain API methods
                        if hasattr(chain, '__getitem__'):
                            block_info = chain[block_number]
                            timestamp = block_info.timestamp
                        elif hasattr(chain, 'get_block'):
                            block_info = chain.get_block(block_number)
                            timestamp = block_info.timestamp
                        else:
                            # Use current timestamp as fallback
                            import time
                            timestamp = int(time.time())
                            logger.debug(f"Using current timestamp as fallback for block {block_number}")
                            
                        # Cache the fallback timestamp too
                        if len(self.block_timestamp_cache) >= 1000:
                            oldest_key = next(iter(self.block_timestamp_cache))
                            del self.block_timestamp_cache[oldest_key]
                        self.block_timestamp_cache[block_number] = timestamp
                        
                    except Exception as chain_error:
                        # Use current timestamp as last resort
                        import time
                        timestamp = int(time.time())
                        logger.debug(f"Using current timestamp as fallback for block {block_number}")
                        
                        # Cache even the fallback
                        if len(self.block_timestamp_cache) >= 1000:
                            oldest_key = next(iter(self.block_timestamp_cache))
                            del self.block_timestamp_cache[oldest_key]
                        self.block_timestamp_cache[block_number] = timestamp
            
            # Safely convert price to Decimal with proper error handling
            try:
                if price is None:
                    return None, None, "Price is None after fetching"
                    
                # Handle different numeric types that ypricemagic might return
                if hasattr(price, 'item'):  # numpy types
                    price_value = float(price.item())
                elif isinstance(price, (int, float)):
                    price_value = float(price)
                else:
                    # Try to convert whatever it is to float first
                    price_value = float(price)
                
                # Convert to Decimal after ensuring it's a standard Python float
                price_decimal = Decimal(str(price_value))
                
                return price_decimal, timestamp, None
                
            except (ValueError, TypeError, decimal.InvalidOperation) as conversion_error:
                error_msg = f"Failed to convert price {price} (type: {type(price)}) to Decimal: {conversion_error}"
                logger.debug(error_msg)
                return None, None, error_msg
            
        except Exception as e:
            error_msg = f"Failed to fetch price for {token_address} at block {block_number}: {e}"
            logger.debug(error_msg)
            return None, None, error_msg
    
    def store_token_price(self, chain_id: int, block_number: int, token_address: str, 
                         price_usd: Decimal, timestamp: int, txn_timestamp: int = None) -> bool:
        """Store token price in database with transaction timestamp"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address, 
                        price_usd, timestamp, txn_timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (chain_id, block_number, token_address, source) 
                    DO UPDATE SET 
                        price_usd = EXCLUDED.price_usd,
                        timestamp = EXCLUDED.timestamp,
                        txn_timestamp = EXCLUDED.txn_timestamp,
                        created_at = NOW()
                """, (
                    chain_id, block_number, self._checksum_address(token_address),
                    price_usd, timestamp, txn_timestamp, 'ypricemagic'
                ))
                return True
                
        except Exception as e:
            logger.error(f"Failed to store price for {token_address}: {e}")
            return False
    
    def _fetch_and_store_eth_price(self, chain_id: int, block_number: int, timestamp: int, txn_timestamp: int = None) -> None:
        """Automatically fetch and store ETH price for this block (ypricemagic only)"""
        eth_address = self._checksum_address("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE")
        
        try:
            # Check if ETH price already exists for this block
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM token_prices 
                    WHERE chain_id = %s AND block_number = %s AND token_address = %s AND source = 'ypricemagic'
                """, (chain_id, block_number, eth_address))
                
                if cursor.fetchone():
                    logger.debug(f"ETH price already exists for chain {chain_id} block {block_number}")
                    return
            
            # Fetch ETH price using ypricemagic
            eth_price_usd, _, error_msg = self.fetch_token_price(eth_address, block_number)
            
            if eth_price_usd is not None:
                # Store ETH price with transaction timestamp
                if self.store_token_price(chain_id, block_number, eth_address, eth_price_usd, timestamp, txn_timestamp):
                    logger.debug(f"✅ Auto-fetched ETH price for block {block_number}: ${eth_price_usd}")
                else:
                    logger.debug(f"❌ Failed to store ETH price for block {block_number}")
            else:
                logger.debug(f"❌ Failed to fetch ETH price for block {block_number}: {error_msg}")
                
        except Exception as e:
            logger.debug(f"Error auto-fetching ETH price for block {block_number}: {e}")
    
    def mark_request_completed(self, request_id: int) -> None:
        """Mark request as completed"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'completed', processed_at = NOW()
                    WHERE id = %s
                """, (request_id,))
                logger.debug(f"Request {request_id} marked as completed")
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as completed: {e}")
    
    def mark_request_failed(self, request_id: int, error_message: str) -> None:
        """Mark request as failed and increment retry count"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'failed', 
                        retry_count = retry_count + 1,
                        error_message = %s,
                        processed_at = NOW()
                    WHERE id = %s
                """, (error_message, request_id))
                logger.debug(f"Request {request_id} marked as failed: {error_message}")
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as failed: {e}")
    
    def reset_failed_requests(self) -> None:
        """Reset old failed requests for retry"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'pending'
                    WHERE status = 'failed' 
                      AND retry_count < 3
                      AND processed_at < NOW() - INTERVAL '1 hour'
                """)
                if cursor.rowcount > 0:
                    logger.info(f"Reset {cursor.rowcount} failed requests for retry")
        except Exception as e:
            logger.error(f"Failed to reset failed requests: {e}")
    
    def force_retry_all_failed(self) -> None:
        """Force retry ALL failed requests immediately (for debugging)"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'pending', retry_count = 0
                    WHERE status = 'failed'
                """)
                if cursor.rowcount > 0:
                    logger.info(f"🔄 Force reset {cursor.rowcount} failed requests for retry")
                else:
                    logger.info("No failed requests found to reset")
        except Exception as e:
            logger.error(f"Failed to force reset failed requests: {e}")
    
    def reset_stale_processing_requests(self) -> None:
        """Reset 'processing' requests that are likely from crashed service instances"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'pending', 
                        retry_count = retry_count + 1,
                        error_message = 'Reset from stale processing state (service restart)'
                    WHERE status = 'processing' 
                      AND retry_count < 3
                      AND processed_at < NOW() - INTERVAL '5 minutes'
                """)
                if cursor.rowcount > 0:
                    logger.info(f"🔄 Reset {cursor.rowcount} stale 'processing' requests back to 'pending' (likely from service crash)")
        except Exception as e:
            logger.error(f"Failed to reset stale processing requests: {e}")
    
    def process_request(self, request: dict, remaining_count: int) -> None:
        """Process a single price request"""
        request_id = request['id']
        chain_id = request['chain_id']
        block_number = request['block_number']
        token_address = request['token_address']
        request_type = request.get('request_type', 'unknown')
        txn_timestamp = request.get('txn_timestamp')  # Extract transaction timestamp
        
        # Get token symbol for better logging
        token_symbol = self.get_token_symbol(chain_id, token_address)
        token_display = f"{token_address} ({token_symbol})" if token_symbol else token_address
        
        # Single log message for starting processing
        logger.info(f"[{remaining_count} remaining] Processing {token_display} at block {block_number} (req {request_id})")
        
        try:
            # Mark as processing
            self.mark_request_processing(request_id)
            
            # Only process chain_id 1 (mainnet) for now
            if chain_id != 1:
                logger.info(f"[{remaining_count-1} remaining] ❌ Skipped {token_address} - unsupported chain {chain_id}")
                self.mark_request_failed(request_id, f"Chain {chain_id} not supported")
                return
            
            # Fetch price
            price_usd, timestamp, error_msg = self.fetch_token_price(token_address, block_number)
            
            if price_usd is None:
                logger.info(f"[{remaining_count-1} remaining] ❌ Failed {token_address} - {error_msg or 'price fetch failed'}")
                self.mark_request_failed(request_id, error_msg or "Failed to fetch price from ypricemagic")
                return
            
            # Store price with transaction timestamp
            if self.store_token_price(chain_id, block_number, token_address, price_usd, timestamp, txn_timestamp):
                self.mark_request_completed(request_id)
                logger.info(f"[{remaining_count-1} remaining] ✅ Completed {token_address} = ${price_usd}")
                
                # Always fetch ETH price for this block (ypricemagic only)
                self._fetch_and_store_eth_price(chain_id, block_number, timestamp, txn_timestamp)
                
            else:
                logger.info(f"[{remaining_count-1} remaining] ❌ Failed {token_address} - database store failed")
                self.mark_request_failed(request_id, "Failed to store price in database")
                
        except Exception as e:
            error_msg = f"Unexpected error in request {request_id}: {str(e)}"
            logger.info(f"[{remaining_count-1} remaining] ❌ Failed {token_address} - {str(e)}")
            logger.debug(f"Request {request_id} traceback: {traceback.format_exc()}")
            self.mark_request_failed(request_id, error_msg)
    
    def run(self) -> None:
        """Main service loop"""
        logger.info("🚀 Starting ypricemagic Price Service")
        
        # Initialize Brownie network
        self._init_brownie_network()
        
        # Reset any stale 'processing' requests from previous crashed instances
        logger.info("🔄 Checking for stale 'processing' requests from previous service instances...")
        self.reset_stale_processing_requests()
        
        loop_count = 0
        cached_requests = []  # Cache for current batch of requests
        
        try:
            while True:
                loop_count += 1
                
                # Reset failed requests every 10 loops (50 seconds)
                # Also check for stale processing requests every 20 loops (100 seconds)
                if loop_count % 10 == 0:
                    self.reset_failed_requests()
                    
                if loop_count % 20 == 0:
                    self.reset_stale_processing_requests()
                
                # If we've processed all cached requests, fetch a new batch
                if not cached_requests:
                    if self.prioritize_failed:
                        cached_requests = self.get_failed_requests()
                        if not cached_requests:
                            cached_requests = self.get_pending_requests()
                    else:
                        cached_requests = self.get_pending_requests()
                
                if cached_requests:
                    # Get total backlog count for reporting
                    total_pending = self.get_total_pending_count()
                    
                    # Process each request in the cached batch
                    while cached_requests:
                        request = cached_requests.pop(0)  # Remove from front of list
                        remaining_in_batch = len(cached_requests)
                        
                        # Calculate total remaining (current batch + any new requests)
                        total_remaining = remaining_in_batch + max(0, total_pending - 50)
                        
                        self.process_request(request, total_remaining + 1)  # +1 for current request
                        
                else:
                    logger.debug("No pending price requests")
                
                # Exit after first idle if --once
                if self.once and not cached_requests:
                    logger.info("--once complete; exiting")
                    break

                # Wait before next poll (only when no cached requests to process)
                if not cached_requests:
                    time.sleep(self.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Price service stopped by user")
        except Exception as e:
            logger.error(f"Price service error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='ypricemagic Price Service')
        parser.add_argument('--network', default='electro', help='Brownie network name to connect')
        parser.add_argument('--retry-failed', action='store_true', help='Prioritize failed requests first')
        parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval in seconds when idle')
        parser.add_argument('--once', action='store_true', help='Run a single cycle and exit')
        args = parser.parse_args()
        
        # Import psycopg2 extras for RealDictCursor
        import psycopg2.extras
        
        service = YPriceMagicService(
            network_name=args.network,
            poll_interval=args.poll_interval,
            prioritize_failed=args.retry_failed,
            once=args.once,
        )

        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start price service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
