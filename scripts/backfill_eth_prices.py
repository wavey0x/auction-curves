#!/usr/bin/env python3
"""
Backfill ETH Prices Script
Directly fetches and stores ETH prices for all take blocks using ypricemagic,
bypassing the price_requests queue system entirely.
"""

import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
import argparse
from decimal import Decimal
from typing import Optional, Tuple
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

class ETHPriceBackfillService:
    """Direct ETH price backfill using ypricemagic (bypasses queue system)"""
    
    def __init__(self, dry_run: bool = True, batch_size: int = 10):
        self.db_conn = None
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.eth_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        self.magic = None
        self.block_timestamp_cache = {}
        self._init_database()
        
    def _checksum_address(self, address: str) -> str:
        """Convert address to proper checksum format"""
        try:
            from eth_utils import to_checksum_address
            return to_checksum_address(address)
        except ImportError:
            # Fallback if eth_utils not available - basic checksum
            from web3 import Web3
            return Web3.to_checksum_address(address)
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            if app_mode == 'dev':
                db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5433/auction_dev')
            elif app_mode == 'prod':
                db_url = os.getenv('PROD_DATABASE_URL')
            else:
                logger.error(f"Unsupported APP_MODE: {app_mode}")
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
    
    def _init_ypricemagic(self) -> None:
        """Initialize ypricemagic (same as ypm service)"""
        try:
            from brownie import network, chain, web3
            
            logger.info("🌐 Initializing Brownie network connection...")
            
            # Connect to mainnet for ypricemagic historical data
            target = 'mainnet'  # Use mainnet for historical price data
            if not network.is_connected():
                logger.info(f"Connecting to '{target}' network...")
                network.connect(target)
                logger.info(f"✅ Connected to Brownie network: {network.show_active()}")
            else:
                logger.info(f"✅ Already connected to Brownie network: {network.show_active()}")
            
            # Import ypricemagic after network is connected
            try:
                logger.info("📦 Importing ypricemagic...")
                from ypricemagic import magic
                self.magic = magic
                logger.info("✅ ypricemagic initialized successfully")
            except Exception as ypm_error:
                logger.error(f"❌ Failed to initialize ypricemagic: {ypm_error}")
                raise
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize ypricemagic setup: {e}")
            sys.exit(1)
    
    def get_missing_eth_price_blocks(self):
        """Get blocks that have takes but no ETH prices"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT t.chain_id, t.block_number
                    FROM takes t
                    LEFT JOIN token_prices tp ON (
                        tp.chain_id = t.chain_id 
                        AND tp.block_number = t.block_number 
                        AND tp.token_address = %s
                        AND tp.source = 'ypricemagic'
                    )
                    WHERE t.chain_id = 1  -- Only mainnet for ypricemagic
                      AND tp.id IS NULL  -- No ETH price exists
                    ORDER BY t.chain_id, t.block_number
                """, (self._checksum_address(self.eth_address),))
                
                results = cursor.fetchall()
                logger.info(f"Found {len(results)} blocks missing ETH prices")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get missing ETH price blocks: {e}")
            return []
    
    def fetch_eth_price(self, block_number: int) -> Tuple[Optional[Decimal], Optional[int], Optional[str]]:
        """Fetch ETH price using ypricemagic at specific block"""
        try:
            from brownie import web3
            
            # Use ypricemagic to get ETH price
            try:
                price = self.magic.get_price(self.eth_address, block=block_number, sync=True)
            except Exception as ypm_error:
                return None, None, f"ypricemagic error: {str(ypm_error)}"
            
            if price is None or price <= 0:
                return None, None, f"ypricemagic returned invalid price: {price}"
            
            # Get block timestamp with caching
            if block_number in self.block_timestamp_cache:
                timestamp = self.block_timestamp_cache[block_number]
            else:
                try:
                    block_info = web3.eth.get_block(block_number)
                    timestamp = block_info['timestamp']
                    
                    # Simple cache with size limit
                    if len(self.block_timestamp_cache) >= 1000:
                        oldest_key = next(iter(self.block_timestamp_cache))
                        del self.block_timestamp_cache[oldest_key]
                    
                    self.block_timestamp_cache[block_number] = timestamp
                    
                except Exception as block_error:
                    return None, None, f"Failed to get block timestamp: {block_error}"
            
            return Decimal(str(price)), timestamp, None
            
        except Exception as e:
            return None, None, f"Unexpected error: {str(e)}"
    
    def store_eth_price(self, chain_id: int, block_number: int, price_usd: Decimal, timestamp: int) -> bool:
        """Store ETH price directly in token_prices table"""
        try:
            if self.dry_run:
                logger.debug(f"[DRY RUN] Would store ETH price: chain {chain_id} block {block_number} = ${price_usd:.4f}")
                return True
                
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address, 
                        price_usd, timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, 'ypricemagic', NOW())
                    ON CONFLICT (chain_id, block_number, token_address, source) 
                    DO UPDATE SET 
                        price_usd = EXCLUDED.price_usd,
                        timestamp = EXCLUDED.timestamp,
                        created_at = NOW()
                """, (
                    chain_id, block_number, self._checksum_address(self.eth_address),
                    price_usd, timestamp
                ))
                
                if cursor.rowcount > 0:
                    logger.debug(f"✅ Stored ETH price: block {block_number} = ${price_usd:.4f}")
                    return True
                else:
                    logger.debug(f"⚠️ ETH price update/conflict for block {block_number}")
                    return True  # Still consider success
                    
        except Exception as e:
            logger.error(f"Failed to store ETH price for block {block_number}: {e}")
            return False
    
    def run_backfill(self) -> None:
        """Main backfill process"""
        logger.info("🚀 Starting ETH Price Backfill (Direct ypricemagic)")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        logger.info(f"Batch size: {self.batch_size}")
        
        # Initialize ypricemagic
        self._init_ypricemagic()
        
        # Get blocks missing ETH prices
        missing_blocks = self.get_missing_eth_price_blocks()
        if not missing_blocks:
            logger.info("✅ No missing ETH prices found - all blocks have ETH prices!")
            return
        
        logger.info(f"Processing {len(missing_blocks)} blocks missing ETH prices...")
        
        success_count = 0
        failure_count = 0
        
        for i, block_info in enumerate(missing_blocks, 1):
            chain_id = block_info['chain_id']
            block_number = block_info['block_number']
            
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(missing_blocks)} blocks processed")
            
            try:
                # Fetch ETH price
                price_usd, timestamp, error_msg = self.fetch_eth_price(block_number)
                
                if price_usd is not None:
                    # Store price
                    if self.store_eth_price(chain_id, block_number, price_usd, timestamp):
                        success_count += 1
                        logger.debug(f"✅ Block {block_number}: ${price_usd:.4f}")
                    else:
                        failure_count += 1
                        logger.debug(f"❌ Failed to store price for block {block_number}")
                else:
                    failure_count += 1
                    logger.debug(f"❌ Failed to fetch price for block {block_number}: {error_msg}")
                
                # Small delay between requests
                if not self.dry_run:
                    time.sleep(0.2)
                    
            except Exception as e:
                logger.error(f"Error processing block {block_number}: {e}")
                failure_count += 1
        
        # Final summary
        logger.info(f"✅ ETH Price Backfill Complete")
        logger.info(f"📊 Summary:")
        logger.info(f"   • Blocks processed: {len(missing_blocks)}")
        logger.info(f"   • Successful: {success_count}")
        logger.info(f"   • Failed: {failure_count}")
        logger.info(f"   • Success rate: {success_count/len(missing_blocks)*100:.1f}%")
        
        if self.dry_run:
            logger.info("🔍 This was a DRY RUN - no actual prices were stored")
            logger.info("Run with --execute to actually store the ETH prices")

def main():
    parser = argparse.ArgumentParser(description='Backfill ETH Prices for Take Blocks')
    parser.add_argument('--execute', action='store_true',
                       help='Actually store the prices (default is dry run)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of blocks to process in each batch (default: 10)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Create service instance
    service = ETHPriceBackfillService(
        dry_run=not args.execute,
        batch_size=args.batch_size
    )
    
    try:
        service.run_backfill()
    except Exception as e:
        logger.error(f"Backfill service failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()