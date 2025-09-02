#!/usr/bin/env python3
"""
Backfill Script for Governance Addresses
Populates NULL governance addresses for existing auctions by querying blockchain contracts

Usage:
    # Run from project root with virtual environment activated
    source venv/bin/activate
    python3 scripts/backfill_governance.py
    
    # Or run directly (will attempt to find venv)
    ./scripts/backfill_governance.py
"""

import os
import sys
import json
import yaml
import logging
import argparse
from typing import Dict, List, Optional

# Try to auto-activate virtual environment if not already active
if 'VIRTUAL_ENV' not in os.environ:
    venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv')
    if os.path.exists(venv_path):
        activate_this = os.path.join(venv_path, 'bin', 'activate_this.py')
        if os.path.exists(activate_this):
            exec(open(activate_this).read(), dict(__file__=activate_this))
        else:
            print("Warning: Virtual environment found but activation script missing.")
            print("Please run: source venv/bin/activate")
    else:
        print("Warning: No virtual environment found. Please run: source venv/bin/activate")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Required dependencies not found: {e}")
    print("Please run: source venv/bin/activate && pip install -r requirements-working.txt")
    sys.exit(1)

# Add parent directory to Python path to import indexer modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indexer.indexer import AuctionIndexer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GovernanceBackfill:
    """Backfill governance addresses for existing auctions"""
    
    def __init__(self, config_path: str = "indexer/config.yaml"):
        """Initialize with config and database connection"""
        self.config_path = config_path
        
        # Load config using indexer's method to ensure consistency
        indexer = AuctionIndexer(config_path)
        self.config = indexer.config
        self.contract_abis = indexer.contract_abis
        
        # Initialize database connection
        self._init_database()
        
        # Web3 connections
        self.web3_connections = {}
        
        # Address normalization cache
        self.normalized_addresses = {}
    
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            self.db_conn = psycopg2.connect(
                self.config['database']['url'],
                cursor_factory=RealDictCursor
            )
            self.db_conn.autocommit = True
            logger.info("Database connection established")
            
            # Test connection
            with self.db_conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def _normalize_address(self, address_raw) -> str:
        """Normalize address to checksummed format (reuse indexer logic)"""
        # Check cache first
        cache_key = str(address_raw)
        if cache_key in self.normalized_addresses:
            return self.normalized_addresses[cache_key]
        
        # Handle both string and int addresses (YAML parsing issue)
        if isinstance(address_raw, int):
            # Handle large integers that represent Ethereum addresses
            if address_raw > 0:
                address_hex = f"0x{address_raw:040x}"
            else:
                logger.warning(f"Invalid integer address: {address_raw}")
                return "0x0000000000000000000000000000000000000000"
        else:
            address_hex = str(address_raw)
        
        # Convert to checksummed address
        try:
            checksummed = Web3.to_checksum_address(address_hex)
            logger.debug(f"Successfully checksummed address: {checksummed}")
        except Exception as e:
            # Fallback if checksum conversion fails
            logger.warning(f"Failed to checksum address {address_hex}, using lowercase: {e}")
            checksummed = address_hex.lower()
        
        # Cache the result
        self.normalized_addresses[cache_key] = checksummed
        return checksummed
    
    def _init_web3_connection(self, network_name: str, network_config: Dict) -> Optional[Web3]:
        """Initialize Web3 connection for a network"""
        try:
            w3 = Web3(Web3.HTTPProvider(network_config['rpc_url']))
            
            # Add PoA middleware for some networks
            if network_config['chain_id'] in [137, 8453]:  # Polygon, Base
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
            # Test connection
            if not w3.is_connected():
                raise Exception(f"Failed to connect to {network_name}")
                
            latest_block = w3.eth.get_block('latest')
            logger.info(f"Connected to {network_name} (chain_id: {network_config['chain_id']}, block: {latest_block['number']})")
            
            return w3
            
        except Exception as e:
            logger.error(f"Failed to initialize {network_name}: {e}")
            return None
    
    def _get_contract_instance(self, w3: Web3, address: str, contract_type: str):
        """Get contract instance for given address and type"""
        abi = self.contract_abis.get(contract_type)
        if not abi:
            raise ValueError(f"Unknown contract type: {contract_type}")
        
        return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
    
    def get_auctions_with_null_governance(self) -> List[Dict]:
        """Get all auctions that have NULL governance addresses"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT auction_address, chain_id, version, factory_address
                    FROM auctions 
                    WHERE governance IS NULL
                    ORDER BY chain_id, auction_address
                """)
                
                auctions = cursor.fetchall()
                logger.info(f"Found {len(auctions)} auctions with NULL governance addresses")
                return auctions
                
        except Exception as e:
            logger.error(f"Failed to query auctions with NULL governance: {e}")
            return []
    
    def backfill_auction_governance(self, auction_address: str, chain_id: int, version: str) -> Optional[str]:
        """Fetch governance address for a specific auction from blockchain"""
        try:
            # Get Web3 connection for this chain
            if chain_id not in self.web3_connections:
                # Find network config for this chain
                network_config = None
                network_name = None
                for name, config in self.config['networks'].items():
                    if config['chain_id'] == chain_id:
                        network_config = config
                        network_name = name
                        break
                
                if not network_config:
                    logger.error(f"No network config found for chain_id {chain_id}")
                    return None
                
                # Initialize Web3 connection
                w3 = self._init_web3_connection(network_name, network_config)
                if not w3:
                    return None
                
                self.web3_connections[chain_id] = w3
            
            w3 = self.web3_connections[chain_id]
            
            # Determine contract type based on version
            contract_type = 'auction' if version == '0.1.0' else 'legacy_auction'
            
            # Create contract instance
            auction_contract = self._get_contract_instance(w3, auction_address, contract_type)
            
            # Call governance() function
            governance_address = auction_contract.functions.governance().call()
            governance_address = self._normalize_address(governance_address)
            
            logger.debug(f"Retrieved governance {governance_address[:5]}..{governance_address[-4:]} for auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id}")
            return governance_address
            
        except Exception as e:
            logger.error(f"Failed to fetch governance for auction {auction_address} on chain {chain_id}: {e}")
            return None
    
    def update_auction_governance(self, auction_address: str, chain_id: int, governance_address: str) -> bool:
        """Update governance address in database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE auctions 
                    SET governance = %s
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (governance_address, auction_address, chain_id))
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Updated governance for auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id}: {governance_address[:5]}..{governance_address[-4:]}")
                    return True
                else:
                    logger.warning(f"No rows updated for auction {auction_address} on chain {chain_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update governance in database: {e}")
            return False
    
    def run_backfill(self, chains: Optional[List[int]] = None) -> Dict[str, int]:
        """Run the backfill process for specified chains (or all chains)"""
        stats = {
            'total': 0,
            'updated': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Get all auctions with NULL governance
        auctions = self.get_auctions_with_null_governance()
        
        # Filter by chains if specified
        if chains:
            auctions = [a for a in auctions if a['chain_id'] in chains]
            logger.info(f"Filtering to chains {chains}: {len(auctions)} auctions to process")
        
        stats['total'] = len(auctions)
        
        if stats['total'] == 0:
            logger.info("No auctions found with NULL governance addresses")
            return stats
        
        # Process each auction
        for auction in auctions:
            auction_address = auction['auction_address']
            chain_id = auction['chain_id']
            version = auction['version']
            
            logger.info(f"Processing auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id} (version: {version})")
            
            # Fetch governance address from blockchain
            governance_address = self.backfill_auction_governance(auction_address, chain_id, version)
            
            if governance_address:
                # Update database
                if self.update_auction_governance(auction_address, chain_id, governance_address):
                    stats['updated'] += 1
                else:
                    stats['failed'] += 1
            else:
                logger.error(f"Failed to retrieve governance for {auction_address} on chain {chain_id}")
                stats['failed'] += 1
        
        # Print summary
        logger.info("=" * 60)
        logger.info("BACKFILL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total auctions processed: {stats['total']}")
        logger.info(f"Successfully updated:     {stats['updated']}")
        logger.info(f"Failed:                  {stats['failed']}")
        logger.info(f"Success rate:            {stats['updated']/stats['total']*100:.1f}%" if stats['total'] > 0 else "N/A")
        logger.info("=" * 60)
        
        return stats


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backfill governance addresses for existing auctions')
    parser.add_argument('--config', '-c',
                       help='Path to config file',
                       default='indexer/config.yaml')
    parser.add_argument('--chains',
                       help='Comma-separated list of chain IDs to process (default: all)',
                       default=None)
    parser.add_argument('--dry-run',
                       help='Show what would be updated without making changes',
                       action='store_true')
    
    args = parser.parse_args()
    
    # Parse chains
    chains = None
    if args.chains:
        try:
            chains = [int(c.strip()) for c in args.chains.split(',')]
        except ValueError:
            logger.error("Invalid chain IDs provided. Must be comma-separated integers.")
            sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No database updates will be made")
        # For dry run, we would need to modify the backfill class
        logger.error("Dry run mode not implemented yet")
        sys.exit(1)
    
    try:
        # Create and run backfill
        backfill = GovernanceBackfill(args.config)
        stats = backfill.run_backfill(chains)
        
        # Exit with error code if any failures
        if stats['failed'] > 0:
            logger.warning(f"Backfill completed with {stats['failed']} failures")
            sys.exit(1)
        else:
            logger.info("Backfill completed successfully")
            
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()