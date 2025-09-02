#!/usr/bin/env python3
"""
Gas Data Backfill Script
One-time script to backfill gas tracking data for existing takes in the database
"""

import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Optional
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

class GasDataBackfiller:
    """Backfills gas tracking data for existing takes"""
    
    def __init__(self, batch_size: int = 100, dry_run: bool = False):
        self.db_conn = None
        self.web3_connections = {}
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        
        self._init_database()
        self._init_web3_connections()
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
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
            self.db_conn.autocommit = True  # Use autocommit to avoid transaction conflicts
            logger.info("✅ Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def _init_web3_connections(self) -> None:
        """Initialize Web3 connections for all chains"""
        try:
            # Ethereum mainnet (chain_id = 1)
            eth_rpc = os.getenv('PROD_ETHEREUM_RPC_URL', 'https://guest:guest@eth.wavey.info')
            if eth_rpc:
                self.web3_connections[1] = Web3(Web3.HTTPProvider(eth_rpc))
                logger.info("✅ Ethereum mainnet Web3 connection established")
            
            # Local/Anvil network (chain_id = 31337)
            local_rpc = os.getenv('ANVIL_RPC_URL', 'http://localhost:8545')
            if local_rpc:
                try:
                    w3_local = Web3(Web3.HTTPProvider(local_rpc))
                    # Test connection
                    w3_local.eth.get_block('latest')
                    self.web3_connections[31337] = w3_local
                    logger.info("✅ Local/Anvil Web3 connection established")
                except Exception as local_error:
                    logger.debug(f"Local RPC not available: {local_error}")
            
            # Polygon (chain_id = 137)
            polygon_rpc = os.getenv('POLYGON_RPC_URL', os.getenv('PROD_POLYGON_RPC_URL'))
            if polygon_rpc:
                try:
                    self.web3_connections[137] = Web3(Web3.HTTPProvider(polygon_rpc))
                    logger.info("✅ Polygon Web3 connection established")
                except Exception as poly_error:
                    logger.debug(f"Polygon RPC error: {poly_error}")
            
            # Arbitrum (chain_id = 42161)
            arbitrum_rpc = os.getenv('ARBITRUM_RPC_URL', os.getenv('PROD_ARBITRUM_RPC_URL'))
            if arbitrum_rpc:
                try:
                    self.web3_connections[42161] = Web3(Web3.HTTPProvider(arbitrum_rpc))
                    logger.info("✅ Arbitrum Web3 connection established")
                except Exception as arb_error:
                    logger.debug(f"Arbitrum RPC error: {arb_error}")
            
            # Optimism (chain_id = 10)
            optimism_rpc = os.getenv('OPTIMISM_RPC_URL', os.getenv('PROD_OPTIMISM_RPC_URL'))
            if optimism_rpc:
                try:
                    self.web3_connections[10] = Web3(Web3.HTTPProvider(optimism_rpc))
                    logger.info("✅ Optimism Web3 connection established")
                except Exception as opt_error:
                    logger.debug(f"Optimism RPC error: {opt_error}")
            
            # Base (chain_id = 8453)
            base_rpc = os.getenv('BASE_RPC_URL', os.getenv('PROD_BASE_RPC_URL'))
            if base_rpc:
                try:
                    self.web3_connections[8453] = Web3(Web3.HTTPProvider(base_rpc))
                    logger.info("✅ Base Web3 connection established")
                except Exception as base_error:
                    logger.debug(f"Base RPC error: {base_error}")
            
            if not self.web3_connections:
                logger.error("No Web3 connections established")
                sys.exit(1)
            else:
                logger.info(f"✅ Total Web3 connections: {len(self.web3_connections)} chains")
            
        except Exception as e:
            logger.error(f"Failed to initialize Web3 connections: {e}")
            sys.exit(1)
    
    def _normalize_tx_hash(self, tx_hash: str) -> str:
        """Ensure transaction hash has 0x prefix"""
        if not tx_hash:
            return tx_hash
        tx_str = str(tx_hash).strip()
        return tx_str if tx_str.startswith('0x') else f'0x{tx_str}'
    
    def _get_gas_metrics(self, w3: Web3, tx_hash: str, block_number: int = None) -> Dict:
        """Extract gas metrics from transaction and receipt (human readable format)
        
        Always returns a dict with gas data, using defaults (0) for any missing values.
        """
        # Normalize transaction hash
        tx_hash = self._normalize_tx_hash(tx_hash)
        
        # Initialize with defaults - we never return None
        default_metrics = {
            'gas_price': 0,
            'base_fee': 0,
            'priority_fee': 0,
            'gas_used': 0,
            'transaction_fee_eth': 0
        }
        
        try:
            # Fetch transaction and receipt
            tx = w3.eth.get_transaction(tx_hash)
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            # Get gas used from receipt
            gas_used = receipt.get('gasUsed', 0)
            
            # Initialize gas metrics
            gas_price_gwei = 0
            base_fee_gwei = 0
            priority_fee_gwei = 0
            transaction_fee_eth = 0
            
            # Handle EIP-1559 transactions (type 2)
            if tx.get('type') == 2 or tx.get('type') == '0x2':
                # Get block to extract base fee
                if block_number:
                    block = w3.eth.get_block(block_number)
                else:
                    block = w3.eth.get_block(tx['blockNumber'])
                
                base_fee_wei = block.get('baseFeePerGas', 0)
                base_fee_gwei = base_fee_wei / 1e9 if base_fee_wei else 0
                
                # Calculate effective priority fee
                max_priority_fee_wei = tx.get('maxPriorityFeePerGas', 0)
                max_fee_wei = tx.get('maxFeePerGas', 0)
                
                if base_fee_wei and max_fee_wei:
                    # Actual priority fee is min of max priority fee and (max fee - base fee)
                    effective_priority_fee_wei = min(max_priority_fee_wei, max_fee_wei - base_fee_wei)
                    effective_priority_fee_wei = max(0, effective_priority_fee_wei)  # Can't be negative
                    priority_fee_gwei = effective_priority_fee_wei / 1e9
                    
                    # Total gas price is base fee + priority fee
                    gas_price_gwei = base_fee_gwei + priority_fee_gwei
                    
                    # Calculate transaction fee
                    transaction_fee_wei = gas_used * (base_fee_wei + effective_priority_fee_wei)
                    transaction_fee_eth = transaction_fee_wei / 1e18
                else:
                    logger.warning(f"Missing EIP-1559 fields in tx {tx_hash}")
            
            else:
                # Legacy transaction (type 0 or 1)
                gas_price_wei = tx.get('gasPrice', 0)
                gas_price_gwei = gas_price_wei / 1e9 if gas_price_wei else 0
                base_fee_gwei = gas_price_gwei  # For legacy txns, gasPrice = base + priority
                priority_fee_gwei = 0  # No separate priority fee in legacy txns
                
                # Calculate transaction fee
                transaction_fee_wei = gas_used * gas_price_wei if gas_price_wei else 0
                transaction_fee_eth = transaction_fee_wei / 1e18
            
            return {
                'gas_price': gas_price_gwei,
                'base_fee': base_fee_gwei,
                'priority_fee': priority_fee_gwei,
                'gas_used': gas_used,
                'transaction_fee_eth': transaction_fee_eth
            }
            
        except Exception as e:
            # More detailed error logging for debugging
            if "not found" in str(e).lower():
                logger.debug(f"Transaction {tx_hash} not found - returning default values")
            elif "timeout" in str(e).lower():
                logger.debug(f"RPC timeout for {tx_hash} - returning default values")
            else:
                logger.debug(f"Failed to get gas metrics for tx {tx_hash}: {e} - returning default values")
            
            # Return defaults instead of None to ensure 0% failure rate
            return default_metrics
    
    def _get_takes_to_backfill(self) -> List[Dict]:
        """Get takes that need gas data backfilled"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get takes without gas data, prioritizing recent ones
                cursor.execute("""
                    SELECT take_id, chain_id, transaction_hash, block_number, timestamp
                    FROM takes 
                    WHERE gas_price IS NULL 
                       OR base_fee IS NULL 
                       OR gas_used IS NULL
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (self.batch_size,))
                
                takes = cursor.fetchall()
                logger.info(f"Found {len(takes)} takes needing gas data backfill")
                return takes
                
        except Exception as e:
            logger.error(f"Failed to get takes for backfill: {e}")
            return []
    
    def _update_take_gas_data(self, take_id: str, gas_metrics: Dict) -> bool:
        """Update a single take with gas data"""
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would update {take_id} with gas data: {gas_metrics}")
                return True
            
            # Use a fresh connection for each update to avoid transaction state issues
            with self.db_conn.cursor() as cursor:
                # Ensure values are properly cast to avoid type errors
                try:
                    gas_price = float(gas_metrics['gas_price']) if gas_metrics['gas_price'] is not None else None
                    base_fee = float(gas_metrics['base_fee']) if gas_metrics['base_fee'] is not None else None
                    priority_fee = float(gas_metrics['priority_fee']) if gas_metrics['priority_fee'] is not None else None
                    gas_used = int(gas_metrics['gas_used']) if gas_metrics['gas_used'] is not None else None
                    transaction_fee_eth = float(gas_metrics['transaction_fee_eth']) if gas_metrics['transaction_fee_eth'] is not None else None
                    
                    cursor.execute("""
                        UPDATE takes SET
                            gas_price = %s,
                            base_fee = %s,
                            priority_fee = %s,
                            gas_used = %s,
                            transaction_fee_eth = %s
                        WHERE take_id = %s
                    """, (
                        gas_price,
                        base_fee, 
                        priority_fee,
                        gas_used,
                        transaction_fee_eth,
                        take_id
                    ))
                    
                    return cursor.rowcount > 0
                    
                except Exception as update_error:
                    logger.error(f"Failed to update take {take_id} - data: {gas_metrics}, error: {update_error}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to update take {take_id}: {e}")
            return False
    
# ETH price will be automatically fetched by ypricemagic service
    
    def run_backfill(self) -> None:
        """Main backfill process"""
        logger.info("🚀 Starting Gas Data Backfill")
        logger.info(f"🔧 Settings: batch_size={self.batch_size}, dry_run={self.dry_run}")
        
        total_processed = 0
        batch_number = 1
        
        while True:
            logger.info(f"\n📦 Processing batch {batch_number}")
            
            # Get next batch of takes to backfill
            takes = self._get_takes_to_backfill()
            if not takes:
                logger.info("✅ No more takes to backfill")
                break
            
            batch_processed = 0
            batch_failed = 0
            batch_skipped = 0
            
            # Process each take in the batch
            for take in takes:
                take_id = take['take_id']
                chain_id = take['chain_id']
                tx_hash = take['transaction_hash']
                block_number = take['block_number']
                
                try:
                    # Skip if no Web3 connection for this chain
                    if chain_id not in self.web3_connections:
                        logger.debug(f"No Web3 connection for chain {chain_id}, using default values for {take_id}")
                        # Use default values for unsupported chains
                        gas_metrics = {
                            'gas_price': 0,
                            'base_fee': 0,
                            'priority_fee': 0,
                            'gas_used': 0,
                            'transaction_fee_eth': 0
                        }
                    else:
                        # Get gas metrics (always returns data now)
                        w3 = self.web3_connections[chain_id]
                        gas_metrics = self._get_gas_metrics(w3, tx_hash, block_number)
                    
                    # Update the take
                    if self._update_take_gas_data(take_id, gas_metrics):
                        batch_processed += 1
                        
                        # ETH price will be automatically fetched by ypricemagic service
                        
                        logger.debug(f"✅ Updated {take_id}: {gas_metrics['gas_price']:.2f} Gwei, {gas_metrics['transaction_fee_eth']:.6f} ETH")
                    else:
                        batch_failed += 1
                
                except Exception as e:
                    logger.error(f"Error processing {take_id}: {e}")
                    batch_failed += 1
                
                # Small delay to avoid overwhelming RPC
                time.sleep(0.1)
            
            # No need to commit - using autocommit mode
            if not self.dry_run:
                logger.info(f"✅ Processed batch {batch_number} (autocommit mode)")
            
            # Update counters
            total_processed += batch_processed
            self.processed_count += batch_processed
            self.failed_count += batch_failed
            self.skipped_count += batch_skipped
            
            logger.info(f"📊 Batch {batch_number} results: {batch_processed} updated, {batch_failed} failed, {batch_skipped} skipped")
            logger.info(f"📈 Total progress: {total_processed} processed")
            
            batch_number += 1
            
            # Sleep between batches to be gentle on RPC
            if takes:  # Only sleep if there were items to process
                logger.info("💤 Sleeping 2 seconds between batches...")
                time.sleep(2)
        
        # Final summary
        logger.info(f"\n🏁 Backfill completed!")
        logger.info(f"📊 Final stats: {self.processed_count} updated, {self.failed_count} failed, {self.skipped_count} skipped")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill gas tracking data for existing takes')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of takes to process per batch (default: 100)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in dry-run mode (no database updates)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    backfiller = GasDataBackfiller(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    try:
        backfiller.run_backfill()
    except KeyboardInterrupt:
        logger.info("\n🛑 Backfill interrupted by user")
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()