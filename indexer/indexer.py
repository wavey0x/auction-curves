#!/usr/bin/env python3
"""
Custom Web3.py Auction Indexer
Replaces Rindexer with native Python implementation
"""

import os
import sys
import json
import time
import yaml
import logging
import argparse
# datetime imports removed - using Unix timestamps directly
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor
from web3 import Web3
from web3.middleware import geth_poa_middleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuctionIndexer:
    """Custom indexer for auction factory and auction events"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        # Apply log level from config if present
        try:
            level_str = str(self.config.get('indexer', {}).get('log_level', 'INFO')).upper()
            level = getattr(logging, level_str, logging.INFO)
            logger.setLevel(level)
        except Exception:
            pass
        self.db_conn = None
        self.web3_connections = {}
        self.contract_abis = {}
        self.tracked_auctions = {}  # {chain_id: {auction_address: contract_instance}}
        self.enabled_tokens_cache = {}  # {(auction_address, chain_id): [token_addresses]}
        self.normalized_addresses = {}  # Cache for address normalization
        
        # Performance caches
        self.block_cache = {}  # {chain_id: {block_number: block_data}}
        self.decimals_cache = {}  # {chain_token_key: decimals}
        self.token_metadata_cache = {}  # {chain_token_key: token_info}
        self.MAX_BLOCK_CACHE_PER_CHAIN = 1000  # Limit memory usage
        
        # Database batching buffers
        self.takes_buffer = []  # Buffer for take records
        self.tokens_buffer = []  # Buffer for token records
        self.TAKES_BATCH_SIZE = 50  # Conservative batch size
        self.TOKENS_BATCH_SIZE = 20
        
        # Load ABIs
        self._load_abis()
        
        # Initialize database connection
        self._init_database()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load and expand environment variables in config"""
        with open(config_path, 'r') as f:
            config_content = f.read()
            
        # Expand environment variables
        import os
        config_content = os.path.expandvars(config_content)
        
        config = yaml.safe_load(config_content)
        logger.info(f"Loaded configuration for {len(config['networks'])} networks")
        return config
    
    def _load_abis(self) -> None:
        """Load contract ABIs from JSON files"""
        for name, path in self.config['abis'].items():
            full_path = os.path.join(os.path.dirname(__file__), path)
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                    
                # Handle both formats: array (correct) or dict with 'abi' key (Brownie artifact)
                if isinstance(data, dict) and 'abi' in data:
                    self.contract_abis[name] = data['abi']
                elif isinstance(data, list):
                    self.contract_abis[name] = data
                else:
                    raise ValueError(f"Invalid ABI format for {name}")
                    
            except Exception as e:
                logger.error(f"Failed to load ABI {name} from {full_path}: {e}")
                sys.exit(1)
    
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
    
    def _init_web3_connection(self, network_name: str, network_config: Dict) -> Web3:
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
            logger.info(f"[{latest_block['number']}] Connected to {network_name} (chain_id: {network_config['chain_id']})")
            
            return w3
            
        except Exception as e:
            logger.error(f"Failed to initialize {network_name}: {e}")
            return None
    
    def _normalize_transaction_hash(self, tx_hash) -> str:
        """Normalize transaction hash to hex string with 0x prefix"""
        if isinstance(tx_hash, bytes):
            return '0x' + tx_hash.hex()
        else:
            tx_str = str(tx_hash)
            return tx_str if tx_str.startswith('0x') else f'0x{tx_str}'
    
    def _normalize_address(self, address_raw) -> str:
        """Normalize address to checksummed format, handling YAML int conversion"""
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
            from web3 import Web3
            checksummed = Web3.to_checksum_address(address_hex)
            logger.debug(f"Successfully checksummed address: {checksummed}")
        except Exception as e:
            # Fallback if checksum conversion fails
            logger.warning(f"Failed to checksum address {address_hex}, using lowercase: {e}")
            checksummed = address_hex.lower()
        
        # Cache the result
        self.normalized_addresses[cache_key] = checksummed
        return checksummed
    
    def _get_gas_metrics(self, w3: Web3, tx_hash: str, block_number: int = None) -> Dict:
        """Extract gas metrics from transaction and receipt (human readable format)"""
        # Normalize transaction hash (ensure 0x prefix)
        tx_hash = self._normalize_transaction_hash(tx_hash)
        
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
                    block = self._get_block_cached(w3, block_number)
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
            logger.error(f"Failed to get gas metrics for tx {tx_hash}: {e}")
            return {
                'gas_price': 0,
                'base_fee': 0,
                'priority_fee': 0,
                'gas_used': 0,
                'transaction_fee_eth': 0
            }
    
    def _get_block_cached(self, w3: Web3, block_number: int):
        """Get block data with caching to reduce Web3 calls"""
        chain_id = w3.eth.chain_id
        
        # Initialize chain cache if not exists
        if chain_id not in self.block_cache:
            self.block_cache[chain_id] = {}
            
        chain_cache = self.block_cache[chain_id]
        
        # Return cached if exists
        if block_number in chain_cache:
            return chain_cache[block_number]
        
        # Evict oldest blocks if cache too large
        if len(chain_cache) >= self.MAX_BLOCK_CACHE_PER_CHAIN:
            oldest_block = min(chain_cache.keys())
            del chain_cache[oldest_block]
            logger.debug(f"Evicted block {oldest_block} from cache for chain {chain_id}")
        
        # Fetch and cache block
        try:
            block_data = w3.eth.get_block(block_number)
            chain_cache[block_number] = block_data
            logger.debug(f"Cached block {block_number} for chain {chain_id}")
            return block_data
        except Exception as e:
            logger.warning(f"Failed to fetch block {block_number} for chain {chain_id}: {e}")
            raise
    
    def _flush_takes_buffer(self):
        """Safely batch insert takes with proper error handling"""
        if not self.takes_buffer:
            return
        
        try:
            with self.db_conn.cursor() as cursor:
                # Use executemany for batch insert
                cursor.executemany("""
                    INSERT INTO takes (
                        take_id, auction_address, chain_id, round_id, take_seq,
                        taker, from_token, to_token, amount_taken, amount_paid, price,
                        timestamp, seconds_from_round_start,
                        block_number, transaction_hash, log_index,
                        gas_price, base_fee, priority_fee, gas_used, transaction_fee_eth
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chain_id, transaction_hash, log_index, timestamp) DO NOTHING
                """, self.takes_buffer)
                
                inserted = cursor.rowcount
                logger.info(f"✅ Batch inserted {inserted}/{len(self.takes_buffer)} takes")
                
            self.takes_buffer.clear()
            
        except Exception as e:
            logger.error(f"Batch insert failed, falling back to individual inserts: {e}")
            # Fallback: try inserting one by one
            for take_data in self.takes_buffer:
                try:
                    self._insert_single_take(take_data)
                except Exception as single_error:
                    logger.error(f"Failed to insert take {take_data[0]}: {single_error}")
            self.takes_buffer.clear()
    
    def _insert_single_take(self, take_data):
        """Insert a single take (fallback method)"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO takes (
                        take_id, auction_address, chain_id, round_id, take_seq,
                        taker, from_token, to_token, amount_taken, amount_paid, price,
                        timestamp, seconds_from_round_start,
                        block_number, transaction_hash, log_index,
                        gas_price, base_fee, priority_fee, gas_used, transaction_fee_eth
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chain_id, transaction_hash, log_index, timestamp) DO NOTHING
                """, take_data)
        except Exception as e:
            logger.error(f"Failed to insert single take: {e}")
            raise
    
    def _flush_all_buffers(self):
        """Flush all database buffers"""
        try:
            self._flush_takes_buffer()
            # Can add more buffer flushes here in the future
            logger.debug("All buffers flushed")
        except Exception as e:
            logger.error(f"Error flushing buffers: {e}")
    
    def _get_last_indexed_block(self, chain_id: int, factory_address: str) -> int:
        """Get last indexed block for a specific factory on a chain"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT COALESCE(last_indexed_block, start_block) as block_to_use FROM indexer_state WHERE chain_id = %s AND LOWER(factory_address) = LOWER(%s)",
                    (chain_id, factory_address)
                )
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Found existing indexer state for factory {factory_address} on chain {chain_id}: block_to_use={result['block_to_use']}")
                    return result['block_to_use']
                else:
                    # Initialize factory state if not exists
                    logger.info(f"No existing indexer state found for factory {factory_address} on chain {chain_id}, initializing...")
                    return self._initialize_factory_state(chain_id, factory_address)
        except psycopg2.Error as e:
            logger.error(f"Error getting last indexed block for factory {factory_address} on chain {chain_id}: {e}")
            return self._initialize_factory_state(chain_id, factory_address)
    
    def _update_last_indexed_block(self, chain_id: int, factory_address: str, block_number: int) -> None:
        """Update last indexed block for a specific factory on a chain"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                UPDATE indexer_state 
                SET last_indexed_block = %s, updated_at = NOW()
                WHERE chain_id = %s AND LOWER(factory_address) = LOWER(%s)
            """, (block_number, chain_id, factory_address))
    
    def _initialize_factory_state(self, chain_id: int, factory_address: str) -> int:
        """Initialize factory state from config and return start block"""
        # Find factory config to get start block and type
        logger.debug(f"Looking for factory {factory_address} in config for chain {chain_id}")
        for network_name, network_config in self.config['networks'].items():
            if network_config.get('chain_id') == chain_id:
                logger.debug(f"Checking network {network_name} with {len(network_config.get('factories', []))} factories")
                for factory_config in network_config.get('factories', []):
                    # Handle both string and int addresses (YAML parsing issue)
                    config_address = self._normalize_address(factory_config['address'])
                    normalized_factory_address = self._normalize_address(factory_address)
                    
                    logger.debug(f"Factory config: address={factory_config['address']} (type: {type(factory_config['address'])}) -> normalized: {config_address}")
                    logger.debug(f"Looking for: {factory_address} (type: {type(factory_address)}) -> normalized: {normalized_factory_address}")
                    logger.debug(f"Match check: {config_address.lower()} == {normalized_factory_address.lower()} -> {config_address.lower() == normalized_factory_address.lower()}")
                    
                    if config_address.lower() == normalized_factory_address.lower():
                        start_block = factory_config['start_block']
                        factory_type = factory_config['type']
                        
                        # Ensure we use the checksummed version consistently
                        checksummed_factory_address = self._normalize_address(factory_address)
                        
                        # Insert initial state
                        with self.db_conn.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO indexer_state (
                                    chain_id, factory_address, factory_type, 
                                    last_indexed_block, start_block, updated_at
                                ) VALUES (%s, %s, %s, %s, %s, NOW())
                                ON CONFLICT (chain_id, factory_address) DO UPDATE SET
                                    start_block = EXCLUDED.start_block,
                                    factory_type = EXCLUDED.factory_type,
                                    updated_at = NOW()
                            """, (chain_id, checksummed_factory_address, factory_type, start_block, start_block))
                        
                        logger.info(f"Initialized factory {factory_address} on chain {chain_id} starting from block {start_block}")
                        logger.info(f"Database record created: chain_id={chain_id}, factory_address={checksummed_factory_address}, start_block={start_block}, last_indexed_block={start_block}")
                        return start_block
        
        # Default if factory not found in config
        logger.warning(f"Factory {factory_address} not found in config for chain {chain_id}, using block 0")
        return 0
    
    
    def _get_contract_instance(self, w3: Web3, address: str, contract_type: str):
        """Get contract instance for given address and type"""
        abi = self.contract_abis.get(contract_type)
        if not abi:
            raise ValueError(f"Unknown contract type: {contract_type}")
        
        return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
    
    def _process_factory_deployment(self, event, chain_id: int, factory_address: str, factory_type: str) -> None:
        """Process factory deployment event to add new auction"""
        try:
            auction_address = event['args']['auction']
            deployer = event['args'].get('deployer', '0x0000000000000000000000000000000000000000')
            
            block = self._get_block_cached(self.web3_connections[chain_id], event['blockNumber'])
            timestamp = block['timestamp']  # Use Unix timestamp directly
            
            # Get auction contract to fetch parameters
            network_name = self._get_network_name_by_chain_id(chain_id)
            w3 = self.web3_connections[chain_id]
            
            contract_type = 'auction' if factory_type == 'modern' else 'legacy_auction'
            auction_contract = self._get_contract_instance(w3, auction_address, contract_type)
            
            # Fetch auction parameters with fallbacks for different contract versions
            try:
                # Try different function names for different contract versions
                try:
                    price_update_interval = auction_contract.functions.STEP_DURATION().call()
                except:
                    # Fallback for legacy contracts - use default 36 seconds
                    price_update_interval = 36
                
                try:
                    auction_length = auction_contract.functions.auctionLength().call()
                except:
                    # Fallback for legacy contracts - use default value
                    auction_length = 3600  # 1 hour default
                
                # Get want token - for legacy auctions, it's in the event args
                if factory_type == 'legacy':
                    want_token = event['args'].get('want')
                    if not want_token:
                        logger.warning(f"Could not get want token from event for legacy auction {auction_address}")
                        return
                else:
                    # Modern auctions have want() function
                    try:
                        want_token = auction_contract.functions.want().call()
                    except:
                        logger.warning(f"Could not get want token for auction {auction_address}")
                        return
                
                # For step_decay_rate, try to get it or use defaults
                try:
                    step_decay_rate_wei = auction_contract.functions.stepDecayRate().call()
                except:
                    # Default values: 995000000000000000000000000 for modern, 988514020352896179319603200 for legacy
                    step_decay_rate_wei = 995000000000000000000000000 if factory_type == 'modern' else 988514020352896179319603200
                
                # Convert to human-readable decay rate (1 - step_decay_rate)
                # step_decay_rate is in RAY format (1e27), so divide by 1e27 then subtract from 1
                decay_rate = 1.0 - (float(step_decay_rate_wei) / 1e27)
                
                # Get starting price (human-readable)
                try:
                    starting_price_wei = auction_contract.functions.startingPrice().call()
                    # Convert from wei to human-readable (assuming 18 decimals for now)
                    starting_price = float(starting_price_wei) / 1e18
                except:
                    starting_price = 0.0  # Default if not available
                
                # Get governance address
                try:
                    governance_address = auction_contract.functions.governance().call()
                    governance_address = self._normalize_address(governance_address)
                except:
                    logger.warning(f"Could not get governance address for auction {auction_address}")
                    governance_address = None
                
                # Discover and store want_token metadata
                self._discover_and_store_token(want_token, chain_id)
                
                # Ensure all addresses are checksummed
                auction_address = self._normalize_address(auction_address)
                deployer = self._normalize_address(deployer)
                want_token = self._normalize_address(want_token)
                factory_address = self._normalize_address(factory_address)
                
                # Insert or update auction record
                with self.db_conn.cursor() as cursor:
                    logger.debug(f"Inserting/Updating auction for factory {factory_address[:5]}..{factory_address[-4:]}")
                    cursor.execute("""
                        INSERT INTO auctions (
                            auction_address, chain_id, update_interval, 
                            step_decay, decay_rate, auction_length, want_token,
                            deployer, timestamp, factory_address, 
                            version, starting_price, governance
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (auction_address, chain_id) DO UPDATE SET
                            update_interval = EXCLUDED.update_interval,
                            step_decay = EXCLUDED.step_decay,
                            decay_rate = EXCLUDED.decay_rate,
                            auction_length = EXCLUDED.auction_length,
                            want_token = EXCLUDED.want_token,
                            deployer = EXCLUDED.deployer,
                            timestamp = EXCLUDED.timestamp,
                            factory_address = EXCLUDED.factory_address,
                            version = EXCLUDED.version,
                            starting_price = EXCLUDED.starting_price,
                            governance = EXCLUDED.governance
                    """, (
                        auction_address, chain_id, price_update_interval,
                        step_decay_rate_wei, decay_rate, auction_length, want_token,
                        deployer, timestamp, factory_address,
                        '0.1.0' if factory_type == 'modern' else '0.0.1',
                        starting_price, governance_address
                    ))
                
                # Add to tracked auctions
                if chain_id not in self.tracked_auctions:
                    self.tracked_auctions[chain_id] = {}
                self.tracked_auctions[chain_id][auction_address] = auction_contract
                
                # Pre-populate enabled tokens from contract to avoid race conditions
                enabled_tokens = self._get_enabled_tokens_from_contract(auction_address, chain_id)
                if enabled_tokens:
                    logger.debug(f"Pre-populated {len(enabled_tokens)} enabled tokens for new auction {auction_address[:5]}..{auction_address[-4:]}")
                    
                    # Also populate database for UI/API use
                    for token_address in enabled_tokens:
                        try:
                            self._discover_and_store_token(token_address, chain_id)
                            cursor.execute("""
                                INSERT INTO enabled_tokens (
                                    auction_address, chain_id, token_address, 
                                    enabled_at, enabled_at_block, enabled_at_tx_hash
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (auction_address, chain_id, token_address) DO NOTHING
                            """, (
                                auction_address, chain_id, token_address,
                                timestamp, event['blockNumber'], 
                                self._normalize_transaction_hash(event['transactionHash'])
                            ))
                        except Exception as token_error:
                            logger.debug(f"Failed to populate enabled token {token_address}: {token_error}")
                
                logger.info(f"[{event['blockNumber']}] 🚀 Auction deployed: {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id} from factory {factory_address[:5]}..{factory_address[-4:]}")
                
            except Exception as e:
                logger.error(f"Failed to fetch auction parameters for {auction_address}: {e}")
                
        except Exception as e:
            logger.error(f"Failed to process factory deployment event: {e}")
    
    def _process_auction_kicked(self, event, chain_id: int, auction_address: str) -> None:
        """Process auction kicked event to create new round"""
        try:
            from_token = event['args']['from']  # The token being sold
            initial_available_wei = event['args']['available']
            
            # Normalize addresses
            auction_address = self._normalize_address(auction_address)
            from_token = self._normalize_address(from_token)
            
            # Discover and store from_token metadata
            self._discover_and_store_token(from_token, chain_id)
            
            # Convert to human-readable format using actual token decimals
            w3 = self.web3_connections[chain_id]
            from_decimals = self._get_token_decimals(w3, from_token)
            from decimal import Decimal
            initial_available = Decimal(initial_available_wei) / (Decimal(10) ** from_decimals)
            
            block = self._get_block_cached(self.web3_connections[chain_id], event['blockNumber'])
            timestamp = block['timestamp']  # Use Unix timestamp directly
            
            # Get next round ID and auction_length for this auction
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(MAX(round_id), 0) + 1 as next_round_id
                    FROM rounds 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (auction_address, chain_id))
                
                next_round_id = cursor.fetchone()['next_round_id']
                
                # Get auction_length from auctions table
                cursor.execute("""
                    SELECT auction_length 
                    FROM auctions 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (auction_address, chain_id))
                
                auction_row = cursor.fetchone()
                auction_length = auction_row['auction_length'] if auction_row else 86400  # Default to 24 hours
                
                # No need to mark previous rounds as inactive - is_active is now calculated dynamically
                txn_hash = self._normalize_transaction_hash(event['transactionHash'])
                # Calculate round timestamps
                round_start = timestamp
                round_end = timestamp + auction_length
                
                # Insert new round (is_active column removed - now calculated dynamically)
                cursor.execute("""
                    INSERT INTO rounds (
                        auction_address, chain_id, round_id, from_token,
                        kicked_at, timestamp, round_start, round_end,
                        initial_available, available_amount, 
                        block_number, transaction_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    auction_address, chain_id, next_round_id, from_token,
                    timestamp, block['timestamp'], round_start, round_end,
                    initial_available, initial_available, event['blockNumber'], txn_hash
                ))
            
            logger.info(f"[{event['blockNumber']}] ⚪ Created round {next_round_id} for auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id}")
            
            # Queue price requests for both tokens at the kick block
            # Get want_token for this auction
            try:
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT want_token FROM auctions 
                        WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                    """, (auction_address, chain_id))
                    
                    auction_data = cursor.fetchone()
                    if auction_data:
                        want_token = auction_data['want_token']
                        
                        # Queue price requests for both from_token and want_token
                        self._queue_price_request(
                            chain_id, event['blockNumber'], from_token, 'kick',
                            auction_address, next_round_id, timestamp
                        )
                        self._queue_price_request(
                            chain_id, event['blockNumber'], want_token, 'kick',
                            auction_address, next_round_id, timestamp
                        )
                        
            except Exception as price_error:
                logger.warning(f"Failed to queue price requests for kick: {price_error}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process auction kicked event: {e}")
    
    def _process_take(self, event, chain_id: int, auction_address: str) -> None:
        """Process auction take event"""
        try:
            # Event args vary by contract version, adapt as needed
            # Take event: Take(address indexed from, address indexed taker, uint256 amountTaken, uint256 amountPaid)
            taker = self._normalize_address(event['args']['taker'])
            amount_taken = event['args']['amountTaken'] 
            amount_paid = event['args']['amountPaid']
            from_token = self._normalize_address(event['args']['from'])
            auction_address = self._normalize_address(auction_address)
            
            logger.debug(f"Processing Take event: auction={auction_address[:5]}..{auction_address[-4:]}, taker={taker[:5]}..{taker[-4:]}, amount_taken={amount_taken}, amount_paid={amount_paid}")
            
            # Check if from_token is enabled for this auction to filter out spam tokens
            # First try contract state (source of truth), fallback to database
            enabled_tokens = self._get_enabled_tokens_from_contract(auction_address, chain_id)
            
            if enabled_tokens:
                # Use contract result (preferred)
                if self._normalize_address(from_token) not in [self._normalize_address(token) for token in enabled_tokens]:
                    logger.info(f"🚫 Skipping take for spam/disabled token {from_token[:5]}..{from_token[-4:]} on auction {auction_address[:5]}..{auction_address[-4:]} (contract check)")
                    return
            else:
                # Fallback to database check
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 1 FROM enabled_tokens 
                        WHERE LOWER(auction_address) = LOWER(%s) 
                        AND chain_id = %s 
                        AND LOWER(token_address) = LOWER(%s)
                    """, (auction_address, chain_id, from_token))
                    
                    if not cursor.fetchone():
                        logger.info(f"🚫 Skipping take for spam/disabled token {from_token[:5]}..{from_token[-4:]} on auction {auction_address[:5]}..{auction_address[-4:]} (database check)")
                        return
            
            block = self._get_block_cached(self.web3_connections[chain_id], event['blockNumber'])
            timestamp_unix = block['timestamp']  # Unix timestamp
            # Convert to datetime for PostgreSQL timestamp with time zone
            import datetime
            timestamp = datetime.datetime.fromtimestamp(timestamp_unix, tz=datetime.timezone.utc)
            
            # Find the round that was ACTIVE when this take occurred
            with self.db_conn.cursor() as cursor:
                # Find the round where round_start <= take_timestamp < round_end
                cursor.execute("""
                    SELECT round_id, from_token, kicked_at
                    FROM rounds
                    WHERE LOWER(auction_address) = LOWER(%s) 
                      AND chain_id = %s 
                      AND LOWER(from_token) = LOWER(%s)
                      AND round_start <= %s
                      AND round_end > %s
                    ORDER BY kicked_at DESC, round_id DESC
                    LIMIT 1
                """, (auction_address, chain_id, from_token, timestamp_unix, timestamp_unix))
                round_data = cursor.fetchone()
                
                if not round_data:
                    # Fallback: find any active round for this auction at take time (any from_token)
                    cursor.execute("""
                        SELECT round_id, from_token, kicked_at
                        FROM rounds
                        WHERE LOWER(auction_address) = LOWER(%s) 
                          AND chain_id = %s 
                          AND round_start <= %s
                          AND round_end > %s
                        ORDER BY kicked_at DESC, round_id DESC
                        LIMIT 1
                    """, (auction_address, chain_id, timestamp_unix, timestamp_unix))
                    round_data = cursor.fetchone()
                
                if round_data:
                    round_id = round_data['round_id']
                    kicked_at = round_data['kicked_at']
                    
                    # Compute take_seq by counting existing takes for this round
                    cursor.execute("""
                        SELECT COUNT(*) as current_takes 
                        FROM takes 
                        WHERE LOWER(auction_address) = LOWER(%s) 
                        AND chain_id = %s 
                        AND round_id = %s
                    """, (auction_address, chain_id, round_id))
                    current_takes_result = cursor.fetchone()
                    current_takes = current_takes_result['current_takes'] if current_takes_result else 0
                    take_seq = current_takes + 1
                    
                    logger.debug(f"✅ Found active round {round_id} for take at {auction_address[:5]}..{auction_address[-4:]} (take_time={timestamp_unix}, current_takes={current_takes})")
                    # Handle both datetime and Unix timestamp formats for kicked_at
                    if isinstance(kicked_at, (int, float)):
                        seconds_from_start = int(timestamp_unix - kicked_at)
                    else:
                        import datetime
                        if isinstance(kicked_at, datetime.datetime):
                            kicked_at_timestamp = int(kicked_at.timestamp())
                            seconds_from_start = int(timestamp_unix - kicked_at_timestamp)
                        else:
                            seconds_from_start = 0
                    
                    # Handle negative values (should be rare now with fixed round attribution logic)
                    if seconds_from_start < 0:
                        logger.error(f"❌ UNEXPECTED: Negative seconds_from_start ({seconds_from_start}) for take {auction_address[:5]}..{auction_address[-4:]}")
                        logger.error(f"   timestamp_unix: {timestamp_unix}, kicked_at: {kicked_at}")
                        logger.error(f"   This should not happen with correct round attribution - possible data corruption")
                        seconds_from_start = 0  # Default to 0 for negative values
                else:
                    # No active round found at take time; this indicates a data issue
                    round_id = 0
                    take_seq = 1
                    seconds_from_start = 0
                    logger.warning(f"⚠️  No active round found for take at {auction_address[:5]}..{auction_address[-4:]} at timestamp {timestamp_unix}; recording with round_id=0")
                
                # Create take ID
                take_id = f"{auction_address}-{round_id}-{take_seq}"
                
                # Calculate human-readable price (want per 1 from) using human-readable amounts
                from decimal import Decimal, getcontext
                getcontext().prec = 50
                amount_taken_dec = amount_taken if isinstance(amount_taken, Decimal) else Decimal(str(amount_taken))
                amount_paid_dec = amount_paid if isinstance(amount_paid, Decimal) else Decimal(str(amount_paid))
                price = Decimal(0) if amount_taken_dec == 0 else (amount_paid_dec / amount_taken_dec)
                
                # Get want_token for this auction first
                cursor.execute("""
                    SELECT want_token FROM auctions 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (auction_address, chain_id))
                
                auction_data = cursor.fetchone()
                if not auction_data:
                    logger.error(f"❌ Auction {auction_address} not found in database for take processing")
                    return
                    
                want_token = (event.get('wantToken') or auction_data['want_token'])
                txn_hash = self._normalize_transaction_hash(event['transactionHash'])
                # Idempotency: skip if this (chain_id, tx, log_index) already recorded
                cursor.execute(
                    "SELECT 1 FROM takes WHERE chain_id=%s AND transaction_hash=%s AND log_index=%s LIMIT 1",
                    (chain_id, self._normalize_transaction_hash(event['transactionHash']), event['logIndex'])
                )
                if cursor.fetchone():
                    logger.debug(f"Duplicate take skipped: tx={txn_hash} log_index={event['logIndex']}")
                    return

                # Get gas metrics for this transaction
                w3 = self.web3_connections[chain_id]
                gas_metrics = self._get_gas_metrics(w3, txn_hash, event['blockNumber'])

                # Add take to buffer instead of immediate insertion
                take_data = (
                    take_id, auction_address, chain_id, round_id, take_seq,
                    taker, from_token, want_token, amount_taken, amount_paid, price,
                    timestamp, seconds_from_start,
                    event['blockNumber'], txn_hash, event['logIndex'],
                    gas_metrics['gas_price'], gas_metrics['base_fee'], gas_metrics['priority_fee'],
                    gas_metrics['gas_used'], gas_metrics['transaction_fee_eth']
                )
                
                self.takes_buffer.append(take_data)
                logger.debug(f"Added take {take_id} to buffer ({len(self.takes_buffer)}/{self.TAKES_BATCH_SIZE})")
                
                # Flush buffer if full
                if len(self.takes_buffer) >= self.TAKES_BATCH_SIZE:
                    self._flush_takes_buffer()
                
                # Update round statistics if the round exists
                try:
                    if round_id != 0:
                        # Get accurate available amount at the take's block
                        w3 = self.web3_connections[chain_id]
                        contract = self.tracked_auctions.get(chain_id, {}).get(auction_address)
                        available_amount_hr = None
                        try:
                            available_raw = contract.functions.available(Web3.to_checksum_address(from_token)).call(block_identifier=event['blockNumber'])
                            from decimal import Decimal
                            from_decimals = event.get('fromDecimals') if event.get('fromDecimals') is not None else self._get_token_decimals(w3, from_token)
                            available_amount_hr = Decimal(available_raw) / (Decimal(10) ** from_decimals)
                        except Exception as blockchain_error:
                            logger.warning(f"Failed historical available() call: {blockchain_error}")

                        if available_amount_hr is not None:
                            # Set available_amount to on-chain value; recompute volume as initial - available
                            cursor.execute("""
                                UPDATE rounds SET
                                    total_volume_sold = GREATEST(0, initial_available - %s),
                                    available_amount = GREATEST(0, %s)
                                WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s AND round_id = %s
                            """, (available_amount_hr, available_amount_hr, auction_address, chain_id, round_id))
                            logger.debug(f"Updated round {round_id} stats with on-chain available={available_amount_hr}")
                        else:
                            # Fallback: subtract, clamped at 0
                            cursor.execute("""
                                UPDATE rounds SET
                                    total_volume_sold = COALESCE(total_volume_sold, 0) + %s,
                                    available_amount = GREATEST(0, available_amount - %s)
                                WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s AND round_id = %s
                            """, (amount_taken, amount_taken, auction_address, chain_id, round_id))
                            logger.debug(f"Updated round {round_id} stats with calculated available (clamped ≥ 0)")
                        
                        if cursor.rowcount == 0:
                            logger.debug(f"No existing round row to update for {auction_address[:5]}..{auction_address[-4:]} round {round_id}")
                except Exception as update_error:
                    logger.error(f"❌ Failed to update round statistics: {update_error}")
                    # Do not raise; we already recorded the take
            
            logger.info(f"[{event['blockNumber']}] 🫴 Successfully processed take {take_id} on chain {chain_id}")
            
            # Queue price requests for both tokens at the take block
            try:
                # Queue price requests for both from_token and want_token (to_token)
                self._queue_price_request(
                    chain_id, event['blockNumber'], from_token, 'take',
                    auction_address, round_id, timestamp_unix
                )
                
                # want_token should already be in the variable from earlier in the method
                if 'want_token' in locals():
                    self._queue_price_request(
                        chain_id, event['blockNumber'], want_token, 'take', 
                        auction_address, round_id, timestamp_unix
                    )
                
                # ETH price will be automatically fetched by ypricemagic service
                # No need to explicitly queue ETH price requests
                
            except Exception as price_error:
                logger.warning(f"Failed to queue price requests for take: {price_error}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process Take event for auction {auction_address}: {e}")
            tx_hash = event.get('transactionHash', 'unknown')
            if isinstance(tx_hash, bytes):
                tx_hash_str = tx_hash.hex()
            elif tx_hash != 'unknown':
                tx_hash_str = str(tx_hash)
            else:
                tx_hash_str = 'unknown'
            logger.error(f"Event details: block={event.get('blockNumber', 'unknown')}, tx={tx_hash_str}")
            import traceback
            traceback.print_exc()
    
    def _is_spam_token(self, w3: Web3, token_address: str, symbol: str = None) -> bool:
        """Check if a token is likely spam based on heuristics"""
        try:
            # Check if symbol is 'ERC20' (common spam indicator)
            if symbol == 'ERC20':
                logger.debug(f"Token {token_address} detected as spam: symbol is 'ERC20'")
                return True
            
            # Check if totalSupply > 2^150
            try:
                if 'erc20' in self.contract_abis:
                    token_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(token_address),
                        abi=self.contract_abis['erc20']
                    )
                    # Try to get totalSupply
                    total_supply = token_contract.functions.totalSupply().call()
                    # 2^150 = 1427247692705959881058285969449495136382746624
                    if total_supply > 2**150:
                        logger.debug(f"Token {token_address} detected as spam: totalSupply > 2^150 ({total_supply})")
                        return True
            except Exception as e:
                # If we can't get totalSupply, it's not necessarily spam
                logger.debug(f"Could not check totalSupply for {token_address}: {e}")
                
        except Exception as e:
            logger.debug(f"Error checking if token {token_address} is spam: {e}")
        
        return False

    def _get_enabled_tokens_from_contract(self, auction_address: str, chain_id: int) -> List[str]:
        """Get enabled tokens from auction contract with caching"""
        try:
            cache_key = (self._normalize_address(auction_address), chain_id)
            
            # Check cache first
            if cache_key in self.enabled_tokens_cache:
                return self.enabled_tokens_cache[cache_key]
            
            # Get contract instance
            if chain_id not in self.tracked_auctions or auction_address not in self.tracked_auctions[chain_id]:
                logger.debug(f"No contract instance for auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id}")
                return []
            
            auction_contract = self.tracked_auctions[chain_id][auction_address]
            
            # Call getAllEnabledAuctions() on the contract
            if hasattr(auction_contract.functions, 'getAllEnabledAuctions'):
                enabled_auctions = auction_contract.functions.getAllEnabledAuctions().call()
                enabled_tokens = [self._normalize_address(token) for token in enabled_auctions]
                
                # Cache the result
                self.enabled_tokens_cache[cache_key] = enabled_tokens
                logger.debug(f"Cached {len(enabled_tokens)} enabled tokens for auction {auction_address[:5]}..{auction_address[-4:]}")
                
                return enabled_tokens
            else:
                logger.debug(f"Contract {auction_address} doesn't have getAllEnabledAuctions method")
                return []
                
        except Exception as e:
            logger.debug(f"Failed to get enabled tokens from contract {auction_address}: {e}")
            return []
    
    def _discover_and_store_token(self, token_address: str, chain_id: int) -> None:
        """Discover token metadata and store in database if not exists (skip spam tokens)"""
        try:
            # Normalize token address
            token_address = self._normalize_address(token_address)
            
            # Check if token already exists (case-insensitive)
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM tokens 
                    WHERE LOWER(address) = LOWER(%s) AND chain_id = %s
                """, (token_address, chain_id))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"No result from token count query for {token_address}")
                    return
                    
                if result['count'] > 0:
                    return  # Token already exists
            
            # Get Web3 connection for this chain
            w3 = self.web3_connections.get(chain_id)
            if not w3:
                logger.warning(f"No Web3 connection for chain {chain_id}, available chains: {list(self.web3_connections.keys())}")
                return
            
            # Check if ERC20 ABI is loaded
            if 'erc20' not in self.contract_abis:
                logger.error(f"ERC20 ABI not loaded. Available ABIs: {list(self.contract_abis.keys())}")
                return
            
            # Create ERC20 contract instance
            try:
                token_contract = w3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=self.contract_abis['erc20']
                )
            except Exception as contract_error:
                logger.error(f"Failed to create contract instance for {token_address}: {type(contract_error).__name__}: {contract_error}")
                return
            
            # Try to fetch token metadata
            try:
                symbol = None
                name = None
                decimals = None
                
                # Try each method individually with better error handling
                try:
                    symbol = token_contract.functions.symbol().call()
                except Exception as e:
                    logger.debug(f"Failed to get symbol for {token_address}: {e}")
                    
                try:
                    name = token_contract.functions.name().call()
                except Exception as e:
                    logger.debug(f"Failed to get name for {token_address}: {e}")
                    
                try:
                    decimals = token_contract.functions.decimals().call()
                except Exception as e:
                    logger.debug(f"Failed to get decimals for {token_address}: {e}")
                
                # Check if this is a spam token
                if self._is_spam_token(w3, token_address, symbol):
                    logger.warning(f"🚫 Skipping spam token at {token_address} (symbol: {symbol})")
                    return
                
                # Insert token into database
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tokens (
                            address, symbol, name, decimals, chain_id,
                            first_seen, timestamp, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, NOW(), %s, NOW()
                        )
                        ON CONFLICT (address, chain_id) DO UPDATE SET
                            symbol = EXCLUDED.symbol,
                            name = EXCLUDED.name,
                            decimals = EXCLUDED.decimals,
                            updated_at = NOW()
                    """, (
                        token_address, symbol, name, decimals, chain_id, int(time.time())
                    ))
                    
                    if symbol and name:
                        logger.info(f"💾 Caching token: {symbol} ({name}) at {token_address} on chain {chain_id}")
                    else:
                        logger.info(f"💾 Caching token (partial metadata) at {token_address} on chain {chain_id}")
                
            except Exception as contract_error:
                logger.warning(f"Failed to process token contract {token_address}: {type(contract_error).__name__}: {contract_error}")
                # Store token with minimal info (but check for spam first)
                if not self._is_spam_token(w3, token_address):
                    with self.db_conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO tokens (
                            address, chain_id, first_seen, timestamp, updated_at
                        ) VALUES (
                            %s, %s, NOW(), %s, NOW()
                        )
                        ON CONFLICT (address, chain_id) DO UPDATE SET
                            updated_at = NOW()
                    """, (token_address, chain_id, int(time.time())))
                
        except Exception as e:
            logger.error(f"Failed to discover token {token_address}: {type(e).__name__}: {e}")
    
    def _get_network_name_by_chain_id(self, chain_id: int) -> Optional[str]:
        """Get network name by chain ID"""
        for name, config in self.config['networks'].items():
            if config['chain_id'] == chain_id:
                return name
        return None
    
    def _process_auction_enabled(self, event, chain_id: int, auction_address: str) -> None:
        """Process auction enabled event to add token to enabled_tokens array"""
        try:
            from_token = self._normalize_address(event['args']['from'])
            to_token = self._normalize_address(event['args']['to'])  # This should be the auction's want_token
            auction_address = self._normalize_address(auction_address)
            
            # Discover and store the from_token metadata
            self._discover_and_store_token(from_token, chain_id)
            
            # Get block info for metadata
            block = self._get_block_cached(self.web3_connections[chain_id], event['blockNumber'])
            timestamp = block['timestamp']
            
            # Insert into enabled_tokens table (with conflict handling)
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO enabled_tokens (
                        auction_address, chain_id, token_address, 
                        enabled_at, enabled_at_block, enabled_at_tx_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (auction_address, chain_id, token_address) DO NOTHING
                """, (
                    auction_address, chain_id, from_token,
                    timestamp, event['blockNumber'], 
                    self._normalize_transaction_hash(event['transactionHash'])
                ))
                
                if cursor.rowcount > 0:
                    logger.info(f"✅ Added token {from_token} to enabled tokens for auction {auction_address} on chain {chain_id}")
                else:
                    logger.debug(f"Token {from_token} already enabled for auction {auction_address}")
            
            # Clear cache for this auction to force refresh on next access
            cache_key = (self._normalize_address(auction_address), chain_id)
            if cache_key in self.enabled_tokens_cache:
                del self.enabled_tokens_cache[cache_key]
                logger.debug(f"Cleared enabled tokens cache for auction {auction_address[:5]}..{auction_address[-4:]}")
                    
        except Exception as e:
            logger.error(f"Failed to process auction enabled event: {e}")
    
    def _process_governance_transferred(self, event, chain_id: int, auction_address: str) -> None:
        """Process governance transferred event to update governance address"""
        try:
            previous_governance = event['args']['previousGovernance']
            new_governance = event['args']['newGovernance']
            
            # Normalize addresses
            auction_address = self._normalize_address(auction_address)
            previous_governance = self._normalize_address(previous_governance)
            new_governance = self._normalize_address(new_governance)
            
            # Get block info for metadata
            block = self._get_block_cached(self.web3_connections[chain_id], event['blockNumber'])
            timestamp = block['timestamp']
            
            # Update governance address in auctions table
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE auctions 
                    SET governance = %s
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (new_governance, auction_address, chain_id))
                
                if cursor.rowcount > 0:
                    logger.info(f"🔄 Updated governance for auction {auction_address[:5]}..{auction_address[-4:]} on chain {chain_id}: {previous_governance[:5]}..{previous_governance[-4:]} → {new_governance[:5]}..{new_governance[-4:]}")
                else:
                    logger.warning(f"No auction found to update governance for {auction_address} on chain {chain_id}")
                    
        except Exception as e:
            logger.error(f"Failed to process governance transferred event: {e}")
    
    def _detect_takes_from_transfers(self, w3: Web3, chain_id: int, from_block: int, to_block: int) -> None:
        """Detect takes by monitoring Transfer events from auction contracts"""
        if chain_id not in self.tracked_auctions:
            return
        
        auction_addresses = list(self.tracked_auctions[chain_id].keys())
        if not auction_addresses:
            return
        
        # Process auctions in batches to avoid RPC query limits
        BATCH_SIZE = self.config.get('indexer', {}).get('transfer_batch_size', 100)
        for i in range(0, len(auction_addresses), BATCH_SIZE):
            batch = auction_addresses[i:i+BATCH_SIZE]
            try:
                self._detect_transfers_for_batch(w3, chain_id, batch, from_block, to_block)
            except Exception as e:
                logger.error(f"Failed to detect transfers for auction batch {len(batch)} auctions on chain {chain_id}: {e}")
    
    def _detect_transfers_for_batch(self, w3: Web3, chain_id: int, auction_batch: List[str], 
                                   from_block: int, to_block: int) -> None:
        """Detect transfers for a batch of auctions using raw eth_getLogs"""
        try:
            logger.debug(f"🔍 Querying Transfer events for {len(auction_batch)} auctions in batch")
            
            # ERC20 Transfer event signature: Transfer(address,address,uint256)
            transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
            
            # Convert auction addresses to padded hex format for topic filtering
            padded_addresses = []
            for address in auction_batch:
                # Remove '0x' prefix and pad to 32 bytes (64 hex chars)
                padded = address[2:].lower().zfill(64)
                padded_addresses.append('0x' + padded)
            
            # Build filter for transfers FROM any auction in batch
            filter_params = {
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [
                    transfer_topic,      # Topic 0: Transfer event signature
                    padded_addresses     # Topic 1: FROM addresses (auction addresses)
                ]
            }
            
            # Get all Transfer events from these auctions
            logs = w3.eth.get_logs(filter_params)
            
            if logs:
                logger.debug(f"[{to_block}] 🎯 Found {len(logs)} Transfer events from {len(auction_batch)} auctions in blocks {from_block}-{to_block}")
                
                for log in logs:
                    try:
                        self._process_raw_transfer_log(log, chain_id, w3)
                    except Exception as e:
                        logger.error(f"Failed to process Transfer log: {e}")
                        
            else:
                logger.debug(f"No Transfer events found from {len(auction_batch)} auctions")
                
        except Exception as e:
            logger.error(f"Failed to query Transfer events for auction batch: {e}")
    
    def _process_raw_transfer_log(self, log, chain_id: int, w3: Web3) -> None:
        """Process a raw Transfer log as a take using on-chain view for amount_paid.

        - Outgoing transfer (from=auction, to=taker) yields amount_taken (from_token base units)
        - amount_paid computed via getAmountNeeded(..., timestamp) at the same block
        - price stored as 1e18 scaled want-per-from
        """
        try:
            # Extract addresses and values
            auction_address = self._normalize_address('0x' + log['topics'][1].hex()[-40:])
            taker_address = self._normalize_address('0x' + log['topics'][2].hex()[-40:])
            from_token = self._normalize_address(log['address'])
            amount_taken_raw = int(log['data'].hex(), 16)

            block_number = log['blockNumber']
            block = self._get_block_cached(w3, block_number)
            timestamp = int(block['timestamp'])

            # Find auction contract instance
            contract = self.tracked_auctions.get(chain_id, {}).get(auction_address)
            if not contract:
                logger.debug(f"Auction {auction_address[:5]}..{auction_address[-4:]} not tracked on chain {chain_id}; skipping")
                return

            # Resolve want token and decimals
            try:
                want_token = self._normalize_address(contract.functions.want().call(block_identifier=block_number))
            except Exception:
                # Fallback to DB
                with self.db_conn.cursor() as cursor:
                    cursor.execute("SELECT want_token FROM auctions WHERE LOWER(auction_address)=LOWER(%s) AND chain_id=%s", (auction_address, chain_id))
                    row = cursor.fetchone()
                    want_token = row['want_token'] if row and row['want_token'] else None
            if not want_token:
                logger.error(f"Want token unknown for auction {auction_address}")
                return

            from_decimals = self._get_token_decimals(w3, from_token)
            want_decimals = self._get_token_decimals(w3, want_token)

            # Compute amount_paid via on-chain view first
            try:
                amount_paid_raw = contract.functions.getAmountNeeded(from_token, amount_taken_raw, timestamp).call(block_identifier=block_number)
            except Exception as e_gan:
                logger.debug(f"getAmountNeeded failed ({e_gan}); falling back to price()")
                price_scaled = contract.functions.price(from_token, timestamp).call(block_identifier=block_number)
                # price_scaled ~ (price_e18 * 10^want) / 1e18
                amount_paid_raw = (amount_taken_raw * int(price_scaled)) // (10 ** from_decimals)

            # Compute price_e18 (1e18-scaled want per 1 from) and human-readable amounts
            from decimal import Decimal, getcontext
            getcontext().prec = 50
            if amount_taken_raw == 0:
                price_e18 = 0
                amt_taken_hr = Decimal(0)
                amt_paid_hr = Decimal(0)
            else:
                # 1e18 scaled price using raw ints and decimals
                numerator = amount_paid_raw * (10 ** from_decimals) * (10 ** 18)
                denominator = amount_taken_raw * (10 ** want_decimals)
                price_e18 = numerator // denominator
                # Human-readable amounts
                amt_taken_hr = Decimal(amount_taken_raw) / (Decimal(10) ** from_decimals)
                amt_paid_hr = Decimal(amount_paid_raw) / (Decimal(10) ** want_decimals)

            # Normalize tx hash
            tx_hash = log['transactionHash']
            if isinstance(tx_hash, bytes):
                tx_hash = '0x' + tx_hash.hex()
            elif not str(tx_hash).startswith('0x'):
                tx_hash = '0x' + str(tx_hash)

            logger.debug(
                f"Take via Transfer: auction={auction_address[:5]}..{auction_address[-4:]}, from={from_token[:5]}..{from_token[-4:]}, want={want_token[:5]}..{want_token[-4:]}, taker={taker_address[:5]}..{taker_address[-4:]}, "
                f"amount_taken={amount_taken_raw}, amount_paid={amount_paid_raw}, price_e18={price_e18}"
            )

            # Build synthetic event and reuse _process_take
            # Convert amounts to human-readable decimals for DB storage
            amount_taken_hr = amt_taken_hr
            amount_paid_hr = amt_paid_hr

            synthetic_take_event = {
                'args': {
                    'taker': taker_address,
                    'amountTaken': amount_taken_hr,
                    'amountPaid': amount_paid_hr,
                    'from': from_token
                },
                'blockNumber': block_number,
                'transactionHash': tx_hash,
                'logIndex': log['logIndex'],
                'price_e18': int(price_e18),
                'wantToken': want_token,
                'wantDecimals': want_decimals,
                'fromDecimals': from_decimals,
            }

            self._process_take(synthetic_take_event, chain_id, auction_address)

        except Exception as e:
            logger.error(f"Failed to process raw transfer log: {e}")
            tx_hash = log.get('transactionHash')
            if isinstance(tx_hash, bytes):
                tx_hash_str = tx_hash.hex()
            elif tx_hash:
                tx_hash_str = str(tx_hash)
            else:
                tx_hash_str = 'unknown'
            logger.error(f"Log data: block={log.get('blockNumber')}, tx={tx_hash_str}")
    
    def _queue_price_request(self, chain_id: int, block_number: int, token_address: str, 
                           request_type: str, auction_address: str = None, round_id: int = None, 
                           txn_timestamp: int = None) -> None:
        """Queue a price request with transaction timestamp (skip spam tokens)"""
        try:
            # Only queue requests for mainnet (chain_id = 1) for now
            if chain_id != 1:
                logger.debug(f"Skipping price request for non-mainnet chain {chain_id}")
                return
            
            # Normalize token address
            token_address = self._normalize_address(token_address)
            
            # Check if token is spam before queueing
            w3 = self.web3_connections.get(chain_id)
            if w3:
                # First check if we can get symbol from database
                symbol = None
                try:
                    with self.db_conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT symbol FROM tokens 
                            WHERE LOWER(address) = LOWER(%s) AND chain_id = %s
                            LIMIT 1
                        """, (token_address, chain_id))
                        result = cursor.fetchone()
                        if result:
                            symbol = result['symbol']
                except Exception as e:
                    logger.debug(f"Could not fetch symbol from database for {token_address}: {e}")
                
                # Check if spam
                if self._is_spam_token(w3, token_address, symbol):
                    logger.debug(f"🚫 Skipping price request for spam token {token_address}")
                    return
            
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO price_requests (
                        chain_id, block_number, token_address, request_type,
                        auction_address, round_id, txn_timestamp, status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
                    ON CONFLICT (chain_id, block_number, token_address) DO NOTHING
                """, (
                    chain_id, block_number, token_address, request_type,
                    auction_address, round_id, txn_timestamp
                ))
                
                if cursor.rowcount > 0:
                    logger.debug(f"💰 Queued price request: {token_address[:5]}..{token_address[-4:]} at block {block_number} (type: {request_type})")
                else:
                    logger.debug(f"Price request already exists: {token_address[:5]}..{token_address[-4:]} at block {block_number}")
                    
        except Exception as e:
            logger.error(f"Failed to queue price request for {token_address}: {e}")
    
    def _get_token_decimals(self, w3: Web3, token_address: str) -> int:
        """Get token decimals, with caching and fallback to 18"""
        # Check memory cache first
        chain_id = w3.eth.chain_id
        cache_key = f"{chain_id}_{token_address.lower()}"
        if cache_key in self.decimals_cache:
            return self.decimals_cache[cache_key]
        
        # Check if we already know the decimals from database
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT decimals FROM tokens 
                    WHERE LOWER(address) = LOWER(%s) AND chain_id = %s
                    LIMIT 1
                """, (token_address, chain_id))
                result = cursor.fetchone()
                if result and result['decimals'] is not None:
                    # Cache the result
                    self.decimals_cache[cache_key] = result['decimals']
                    return result['decimals']
        except Exception as e:
            logger.debug(f"Could not fetch decimals from database for {token_address[:5]}..{token_address[-4:]}: {e}")
        
        # Try to call decimals() on the token contract
        try:
            erc20_abi = self.contract_abis.get('erc20', [])
            if erc20_abi:
                token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
                decimals = token_contract.functions.decimals().call()
                logger.debug(f"Fetched {decimals} decimals for token {token_address[:5]}..{token_address[-4:]}")
                # Cache the result
                self.decimals_cache[cache_key] = decimals
                return decimals
        except Exception as e:
            logger.debug(f"Could not call decimals() on token {token_address[:5]}..{token_address[-4:]}: {e}")
        
        # Fallback to 18 decimals (most common)
        logger.debug(f"Using fallback 18 decimals for token {token_address[:5]}..{token_address[-4:]}")
        # Cache the fallback result
        self.decimals_cache[cache_key] = 18
        return 18
    
    def _preload_tokens_for_chain(self, chain_id: int) -> None:
        """Load all tokens for a chain into memory at startup"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT address, symbol, name, decimals 
                    FROM tokens 
                    WHERE chain_id = %s
                """, (chain_id,))
                
                loaded_count = 0
                for row in cursor.fetchall():
                    # Cache token metadata
                    cache_key = f"{chain_id}_{row['address'].lower()}"
                    self.token_metadata_cache[cache_key] = row
                    
                    # Cache decimals if available
                    if row['decimals'] is not None:
                        self.decimals_cache[cache_key] = row['decimals']
                    
                    loaded_count += 1
                
                logger.info(f"📚 Pre-loaded {loaded_count} tokens for chain {chain_id}")
                
        except Exception as e:
            logger.error(f"Failed to pre-load tokens for chain {chain_id}: {e}")
    
    def _get_token_metadata_cached(self, token_address: str, chain_id: int) -> Optional[Dict]:
        """Get cached token metadata"""
        cache_key = f"{chain_id}_{token_address.lower()}"
        return self.token_metadata_cache.get(cache_key)
    
    def _process_events_for_network(self, network_name: str, network_config: Dict) -> None:
        """Process events for a specific network"""
        chain_id = network_config['chain_id']
        
        # Initialize Web3 connection
        if chain_id not in self.web3_connections:
            w3 = self._init_web3_connection(network_name, network_config)
            if not w3:
                return
            self.web3_connections[chain_id] = w3
            
        # CRITICAL FIX: Load existing auctions from database so they get tracked for event processing
        if chain_id not in self.tracked_auctions or len(self.tracked_auctions[chain_id]) == 0:
            logger.info(f"🔄 Loading existing auctions from database for chain {chain_id}")
            self._load_existing_auctions(chain_id)
            logger.info(f"After loading: chain {chain_id} has {len(self.tracked_auctions.get(chain_id, {}))} tracked auctions")
            
            # Pre-load token metadata for this chain
            self._preload_tokens_for_chain(chain_id)
        
        w3 = self.web3_connections[chain_id]
        current_block = w3.eth.get_block('latest')['number']
        
        # Process each factory independently
        for factory_config in network_config.get('factories', []):
            self._process_factory_events_for_network(w3, chain_id, factory_config, current_block)
    
    def _process_factory_events_for_network(self, w3: Web3, chain_id: int, factory_config: Dict, current_block: int) -> None:
        """Process events for a specific factory on a network"""
        factory_address_raw = factory_config['address']
        factory_type = factory_config['type']
        
        # Skip if factory address is empty or invalid (from empty environment variables)
        if not factory_address_raw or str(factory_address_raw).strip() in ['', 'None', 'none', 'null']:
            logger.debug(f"Skipping empty/invalid factory address '{factory_address_raw}' on chain {chain_id}")
            return
        
        # Handle both string and int addresses (YAML parsing issue) 
        factory_address = self._normalize_address(factory_address_raw)
        
        # Get last indexed block for this specific factory
        last_indexed_block = self._get_last_indexed_block(chain_id, factory_address)
        blocks_behind = current_block - last_indexed_block
        logger.info(f"[{current_block}, -{blocks_behind}] Factory {factory_address[:5]}..{factory_address[-4:]} on chain {chain_id}: syncing from {last_indexed_block}")
        
        if last_indexed_block >= current_block:
            logger.debug(f"Factory {factory_address} on chain {chain_id} up to date at block {current_block}")
            return
        
        # Process in batches
        batch_size = self.config['indexer']['block_batch_size']
        from_block = last_indexed_block + 1
        
        total_blocks_to_process = current_block - from_block + 1
        logger.info(f"[{current_block}, -{blocks_behind}] Processing {total_blocks_to_process:,} blocks for factory {factory_address[:5]}..{factory_address[-4:]} on chain {chain_id}")
        
        while from_block <= current_block:
            to_block = min(from_block + batch_size - 1, current_block)
            
            # Progress logging every 5000 blocks
            blocks_processed = to_block - last_indexed_block
            if blocks_processed > 0 and blocks_processed % 5000 < batch_size:
                remaining_blocks = current_block - to_block
                percent_complete = (blocks_processed / total_blocks_to_process) * 100 if total_blocks_to_process > 0 else 100
                logger.info(f"[{to_block}, -{remaining_blocks}] Factory {factory_address[:5]}..{factory_address[-4:]} progress: {blocks_processed:,}/{total_blocks_to_process:,} blocks ({percent_complete:.1f}%)")
            
            try:
                # Process factory events for this specific factory
                self._process_factory_events(
                    w3, chain_id, factory_config, from_block, to_block
                )
                
                # Process auction events for tracked auctions on this chain
                self._process_auction_events(w3, chain_id, from_block, to_block)
                
                # Update progress for this specific factory
                self._update_last_indexed_block(chain_id, factory_address, to_block)
                remaining_blocks = current_block - to_block
                logger.debug(f"[{to_block}, -{remaining_blocks}] Factory {factory_address[:5]}..{factory_address[-4:]} processed batch {from_block}-{to_block}")
                
                # Flush any pending batched data
                self._flush_all_buffers()
                
                from_block = to_block + 1
                
            except Exception as e:
                logger.error(f"Failed to process blocks {from_block}-{to_block} for factory {factory_address} on chain {chain_id}: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _process_factory_events(self, w3: Web3, chain_id: int, factory_config: Dict, from_block: int, to_block: int) -> None:
        """Process factory deployment events"""
        factory_address_raw = factory_config['address']
        factory_type = factory_config['type']
        
        # Handle both string and int addresses (YAML parsing issue)
        factory_address = self._normalize_address(factory_address_raw)
        
        if factory_address == "0x0000000000000000000000000000000000000000":
            return  # Skip placeholder addresses
        
        try:
            abi_key = 'auction_factory' if factory_type == 'modern' else 'legacy_auction_factory'
            factory_contract = self._get_contract_instance(w3, factory_address, abi_key)
            
            # Get deployment events using eth_getLogs
            logger.debug(f"Querying {factory_type} factory {factory_address[:5]}..{factory_address[-4:]} events from blocks {from_block}-{to_block}")
            event_cls = factory_contract.events.DeployedNewAuction
            events = self._get_event_logs_with_split(event_cls, from_block, to_block)
            if events:
                logger.info(f"[{to_block}] 👨‍⚖️ Found {len(events)} auction deployment events from factory {factory_address[:5]}..{factory_address[-4:]} in blocks {from_block}-{to_block}")
            
            for event in events:
                self._process_factory_deployment(event, chain_id, factory_address, factory_type)
                
        except Exception as e:
            logger.error(f"Failed to process factory events for {factory_address}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _process_auction_events(self, w3: Web3, chain_id: int, from_block: int, to_block: int) -> None:
        """Process auction events for all tracked auctions"""
            
        total_take_events = 0
        for auction_address, auction_contract in self.tracked_auctions[chain_id].items():
            # Process AuctionKicked events using eth_getLogs
            try:
                if hasattr(auction_contract.events, 'AuctionKicked'):
                    kicked_event = auction_contract.events.AuctionKicked
                    for event in self._get_event_logs_with_split(kicked_event, from_block, to_block):
                        self._process_auction_kicked(event, chain_id, auction_address)
            except Exception:
                logger.error(f"Failed to process AuctionKicked events for {auction_address}: {e}")
                pass  # Event might not exist in this contract version
            
            # Skip traditional Take event processing since Take events don't actually exist
            # All takes are detected via Transfer events instead
            
            # Process AuctionEnabled events using eth_getLogs
            try:
                if hasattr(auction_contract.events, 'AuctionEnabled'):
                    enabled_event = auction_contract.events.AuctionEnabled
                    for event in self._get_event_logs_with_split(enabled_event, from_block, to_block):
                        self._process_auction_enabled(event, chain_id, auction_address)
            except Exception:
                pass  # Event might not exist in this contract version
            
            # Process GovernanceTransferred events using eth_getLogs
            try:
                if hasattr(auction_contract.events, 'GovernanceTransferred'):
                    governance_event = auction_contract.events.GovernanceTransferred
                    for event in self._get_event_logs_with_split(governance_event, from_block, to_block):
                        self._process_governance_transferred(event, chain_id, auction_address)
            except Exception:
                pass  # Event might not exist in this contract version

        # Since Take events don't actually exist, detect all takes via Transfer events
        logger.debug(f"[{to_block}] Running Transfer event detection for takes on chain {chain_id} for blocks {from_block}-{to_block}")
        self._detect_takes_from_transfers(w3, chain_id, from_block, to_block)

    def _get_event_logs_with_split(self, event_cls, from_block: int, to_block: int, 
                                  argument_filters: Dict = None, min_span: int = 500) -> List[Any]:
        """Fetch logs for an event using eth_getLogs with adaptive range splitting.

        - Uses web3.py v6 Event.get_logs() (which calls eth_getLogs under the hood)
        - Splits the block range on provider size/limit errors
        - Supports argument_filters for Transfer events
        """
        try:
            # Build the filter arguments
            filter_args = {'fromBlock': from_block, 'toBlock': to_block}
            if argument_filters:
                filter_args['argument_filters'] = argument_filters
            
            return event_cls.get_logs(**filter_args)
        except Exception as e:
            span = to_block - from_block
            # Common provider errors benefit from splitting: too many results, response size exceeded, timeout
            msg = str(e).lower()
            should_split = span > min_span and any(x in msg for x in [
                'too many results',
                'response size',
                'limit',
                'timeout',
                'gateway',
                'internal error',
                'server error',
            ])
            if should_split:
                mid = from_block + span // 2
                left = self._get_event_logs_with_split(event_cls, from_block, mid, argument_filters, min_span)
                right = self._get_event_logs_with_split(event_cls, mid + 1, to_block, argument_filters, min_span)
                return left + right
            # If not a split-worthy error or span is already small, re-raise so caller can log
            raise
    
    def _load_existing_auctions(self, chain_id: int) -> None:
        """Load existing auctions from database into tracked_auctions"""
        try:
            logger.info(f"🔍 Loading existing auctions from database for chain {chain_id}")
            
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT auction_address, factory_address, version
                    FROM auctions 
                    WHERE chain_id = %s
                """, (chain_id,))
                
                auctions = cursor.fetchall()
                logger.info(f"Found {len(auctions)} auctions in database for chain {chain_id}")
                
                if chain_id not in self.tracked_auctions:
                    self.tracked_auctions[chain_id] = {}
                
                w3 = self.web3_connections[chain_id]
                for auction_data in auctions:
                    address = auction_data['auction_address']
                    factory_address = auction_data['factory_address']
                    version = auction_data.get('version')
                    
                    # If version is not available, deduce it from factory type
                    if not version:
                        # Find factory type by matching factory address
                        factory_type = None
                        for network_config in self.config['networks'].values():
                            if network_config.get('chain_id') == chain_id:
                                for factory in network_config.get('factories', []):
                                    if factory['address'].lower() == factory_address.lower():
                                        factory_type = factory['type']
                                        break
                                break
                        
                        # Determine version based on factory type
                        version = '0.1.0' if factory_type == 'modern' else '0.0.1'
                    
                    contract_type = 'auction' if version == '0.1.0' else 'legacy_auction'
                    logger.debug(f"Creating {contract_type} contract for auction {address[:5]}..{address[-4:]} on chain {chain_id}")
                    
                    try:
                        contract = self._get_contract_instance(w3, address, contract_type)
                        
                        # Debug: Check what events are available
                        logger.debug(f"Contract {address[:5]}..{address[-4:]} events: {list(contract.events.__dict__.keys())}")
                        
                        self.tracked_auctions[chain_id][address] = contract
                        logger.debug(f"Successfully added auction {address[:5]}..{address[-4:]} to tracked auctions for chain {chain_id}")
                    except Exception as e:
                        logger.error(f"Failed to create contract instance for auction {address[-8:]} on chain {chain_id}: {e}")
                        continue
                    
                logger.info(f"Loaded {len(auctions)} existing auctions for chain {chain_id}")
                
        except Exception as e:
            logger.error(f"Failed to load existing auctions for chain {chain_id}: {e}")
    
    def run(self, networks: List[str] = None) -> None:
        """Run the indexer for specified networks"""
        if networks is None:
            networks = list(self.config['networks'].keys())
        
        logger.info(f"🚀 Starting indexer for networks: {', '.join(networks)}")
        
        # Load existing auctions for each network
        for network_name in networks:
            if network_name in self.config['networks']:
                network_config = self.config['networks'][network_name]
                chain_id = network_config['chain_id']
                
                # Initialize connection
                w3 = self._init_web3_connection(network_name, network_config)
                if w3:
                    self.web3_connections[chain_id] = w3
                    self._load_existing_auctions(chain_id)
        
        # Main indexing loop
        poll_interval = self.config['indexer']['poll_interval']
        
        try:
            while True:
                for network_name in networks:
                    if network_name in self.config['networks']:
                        network_config = self.config['networks'][network_name]
                        self._process_events_for_network(network_name, network_config)
                
                logger.debug(f"⏸️  Sleeping for {poll_interval} seconds...")
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Indexer stopped by user")
        except Exception as e:
            logger.error(f"Indexer error: {e}")
            raise
        finally:
            # Ensure all buffers are flushed before exit
            logger.info("Flushing all buffers before exit...")
            self._flush_all_buffers()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Custom Web3 Auction Indexer')
    parser.add_argument('--network', '-n', 
                       help='Comma-separated list of networks to index (default: all)',
                       default=None)
    parser.add_argument('--config', '-c',
                       help='Path to config file',
                       default='config.yaml')
    parser.add_argument('--inspect-tx',
                       help='Inspect a specific transaction hash for Take events',
                       dest='inspect_tx', default=None)
    parser.add_argument('--chain',
                       help='Single network name to use for inspection (e.g., ethereum, polygon)',
                       dest='inspect_chain', default=None)
    
    args = parser.parse_args()
    
    # Parse networks
    networks = None
    if args.network:
        networks = [n.strip() for n in args.network.split(',')]
    
    # Create indexer
    try:
        indexer = AuctionIndexer(args.config)
        # Inspect single transaction if requested
        if args.inspect_tx:
            inspect_networks = [args.inspect_chain] if args.inspect_chain else list(indexer.config['networks'].keys())
            for network_name in inspect_networks:
                if network_name not in indexer.config['networks']:
                    continue
                network_config = indexer.config['networks'][network_name]
                chain_id = network_config['chain_id']
                w3 = indexer._init_web3_connection(network_name, network_config)
                if not w3:
                    continue
                indexer.web3_connections[chain_id] = w3
                indexer._load_existing_auctions(chain_id)
                try:
                    receipt = w3.eth.get_transaction_receipt(args.inspect_tx)
                except Exception as e:
                    logger.info(f"{network_name}: receipt not found or error: {e}")
                    continue
                # Search takes in this receipt for tracked auctions
                total_decoded = 0
                for auction_address, auction_contract in indexer.tracked_auctions.get(chain_id, {}).items():
                    for event_name in ['Take', 'AuctionTake', 'Sale']:
                        if hasattr(auction_contract.events, event_name):
                            try:
                                event_cls = getattr(auction_contract.events, event_name)
                                decoded = event_cls().process_receipt(receipt)
                                for ev in decoded:
                                    logger.info(f"{network_name} Take-like event found: auction={auction_address} taker={ev['args'].get('taker','?')} amountTaken={ev['args'].get('amountTaken','?')} amountPaid={ev['args'].get('amountPaid','?')} block={receipt['blockNumber']}")
                                    total_decoded += 1
                            except Exception:
                                continue
                if total_decoded == 0:
                    logger.info(f"{network_name}: no Take-like events decoded in tx {args.inspect_tx}")
            return
        
        # Otherwise run the full indexer loop
        indexer.run(networks)
    except Exception as e:
        logger.error(f"Failed to start indexer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
