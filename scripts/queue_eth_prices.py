#!/usr/bin/env python3
"""
Queue ETH Price Requests Script
Creates price requests for ETH (0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) 
for all take blocks to ensure comprehensive ETH pricing coverage.
"""

import os
import sys
import logging
import psycopg2
import psycopg2.extras
import argparse
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

class ETHPriceQueueScript:
    """Script to queue ETH price requests for all take blocks"""
    
    def __init__(self, dry_run: bool = True):
        self.db_conn = None
        self.dry_run = dry_run
        self.eth_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            # Use the same database URL as other services
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            if app_mode == 'dev':
                db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://wavey@localhost:5432/auction_dev')
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
    
    def get_all_take_blocks(self):
        """Get all unique chain_id/block_number combinations from takes table"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT chain_id, block_number
                    FROM takes
                    ORDER BY chain_id, block_number
                """)
                results = cursor.fetchall()
                logger.info(f"Found {len(results)} unique take blocks across all chains")
                return results
                
        except Exception as e:
            logger.error(f"Failed to get take blocks: {e}")
            return []
    
    def check_existing_eth_requests(self):
        """Check how many ETH price requests already exist"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM price_requests
                    WHERE token_address = %s
                """, (self.eth_address.lower(),))
                
                count = cursor.fetchone()['count']
                logger.info(f"Found {count} existing ETH price requests")
                return count
                
        except Exception as e:
            logger.error(f"Failed to check existing ETH requests: {e}")
            return 0
    
    def queue_eth_price_request(self, chain_id: int, block_number: int) -> bool:
        """Queue ETH price request for specific block"""
        try:
            if self.dry_run:
                logger.debug(f"[DRY RUN] Would queue ETH price request for chain {chain_id} block {block_number}")
                return True
            
            logger.debug(f"Attempting to insert: chain_id={chain_id}, block_number={block_number}, token_address={self.eth_address.lower()}")
                
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO price_requests (
                        chain_id, block_number, token_address, request_type,
                        status, created_at
                    ) VALUES (%s, %s, %s, 'manual', 'pending', NOW())
                    ON CONFLICT (chain_id, block_number, token_address) DO NOTHING
                """, (chain_id, block_number, self.eth_address.lower()))
                
                if cursor.rowcount > 0:
                    logger.debug(f"✅ Queued ETH price request for chain {chain_id} block {block_number}")
                    return True
                else:
                    logger.debug(f"ETH price request already exists for chain {chain_id} block {block_number}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to queue ETH price request for chain {chain_id} block {block_number}: {e}")
            raise e  # Re-raise so main loop can handle it properly
    
    def run_queue_process(self) -> None:
        """Main process to queue ETH price requests"""
        logger.info("🚀 Starting ETH Price Request Queueing")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        
        # Check existing requests
        existing_count = self.check_existing_eth_requests()
        
        # Get all take blocks
        take_blocks = self.get_all_take_blocks()
        if not take_blocks:
            logger.warning("No take blocks found")
            return
        
        # Queue ETH requests for each unique block
        queued_count = 0
        skipped_count = 0
        failed_count = 0
        
        logger.info(f"Processing {len(take_blocks)} unique take blocks...")
        
        for i, block_info in enumerate(take_blocks, 1):
            chain_id = block_info['chain_id']
            block_number = block_info['block_number']
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(take_blocks)} blocks processed")
            
            try:
                result = self.queue_eth_price_request(chain_id, block_number)
                if result:
                    queued_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing chain {chain_id} block {block_number}: {e}")
                failed_count += 1
        
        # Final summary
        logger.info(f"✅ ETH Price Request Queueing Complete")
        logger.info(f"📊 Summary:")
        logger.info(f"   • Existing ETH requests: {existing_count}")
        logger.info(f"   • Total take blocks: {len(take_blocks)}")
        logger.info(f"   • New requests queued: {queued_count}")
        logger.info(f"   • Already existed (skipped): {skipped_count}")
        logger.info(f"   • Failed: {failed_count}")
        
        if self.dry_run:
            logger.info("🔍 This was a DRY RUN - no actual requests were created")
            logger.info("Run with --execute to actually create the price requests")

def main():
    parser = argparse.ArgumentParser(description='Queue ETH Price Requests for All Take Blocks')
    parser.add_argument('--execute', action='store_true',
                       help='Actually queue the requests (default is dry run)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Create script instance (dry_run=False only if --execute is passed)
    script = ETHPriceQueueScript(dry_run=not args.execute)
    
    try:
        script.run_queue_process()
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()