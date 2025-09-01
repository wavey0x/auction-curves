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
        self.normalized_addresses = {}  # Cache for address normalization
        
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
                    logger.info(f"Loaded ABI: {name} (extracted from Brownie artifact)")
                elif isinstance(data, list):
                    self.contract_abis[name] = data
                    logger.info(f"Loaded ABI: {name} (direct ABI array)")
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
            logger.info(f"Connected to {network_name} (chain_id: {network_config['chain_id']}) at block {latest_block['number']}")
            
            return w3
            
        except Exception as e:
            logger.error(f"Failed to initialize {network_name}: {e}")
            return None
    
    def _normalize_transaction_hash(self, tx_hash) -> str:
        """Normalize transaction hash to hex string with 0x prefix"""
        if isinstance(tx_hash, bytes):
            return tx_hash.hex()
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
            
            block = self.web3_connections[chain_id].eth.get_block(event['blockNumber'])
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
                
                # Discover and store want_token metadata
                self._discover_and_store_token(want_token, chain_id)
                
                # Ensure all addresses are checksummed
                auction_address = self._normalize_address(auction_address)
                deployer = self._normalize_address(deployer)
                want_token = self._normalize_address(want_token)
                factory_address = self._normalize_address(factory_address)
                
                # Insert or update auction record
                with self.db_conn.cursor() as cursor:
                    logger.debug(f"Inserting/Updating auction for factory {factory_address[-8:]}")
                    cursor.execute("""
                        INSERT INTO auctions (
                            auction_address, chain_id, update_interval, 
                            step_decay, decay_rate, auction_length, want_token,
                            deployer, timestamp, factory_address, 
                            version, starting_price
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
                            starting_price = EXCLUDED.starting_price
                    """, (
                        auction_address, chain_id, price_update_interval,
                        step_decay_rate_wei, decay_rate, auction_length, want_token,
                        deployer, timestamp, factory_address,
                        '0.1.0' if factory_type == 'modern' else '0.0.1',
                        starting_price
                    ))
                
                # Add to tracked auctions
                if chain_id not in self.tracked_auctions:
                    self.tracked_auctions[chain_id] = {}
                self.tracked_auctions[chain_id][auction_address] = auction_contract
                
                logger.info(f"Added auction {auction_address} on chain {chain_id} from factory {factory_address}")
                
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
            
            # Convert to human-readable format (assume 18 decimals for now)
            # TODO: Get actual token decimals from tokens table
            initial_available = float(initial_available_wei) / 1e18
            
            block = self.web3_connections[chain_id].eth.get_block(event['blockNumber'])
            timestamp = block['timestamp']  # Use Unix timestamp directly
            
            # Get next round ID for this auction
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COALESCE(MAX(round_id), 0) + 1 as next_round_id
                    FROM rounds 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (auction_address, chain_id))
                
                next_round_id = cursor.fetchone()['next_round_id']
                
                # Mark previous rounds as inactive
                cursor.execute("""
                    UPDATE rounds 
                    SET is_active = FALSE 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s AND is_active = TRUE
                """, (auction_address, chain_id))
                txn_hash = self._normalize_transaction_hash(event['transactionHash'])
                # Insert new round
                cursor.execute("""
                    INSERT INTO rounds (
                        auction_address, chain_id, round_id, from_token,
                        kicked_at, timestamp, initial_available, is_active,
                        available_amount, block_number, transaction_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s
                    )
                """, (
                    auction_address, chain_id, next_round_id, from_token,
                    timestamp, block['timestamp'], initial_available, initial_available,
                    event['blockNumber'], txn_hash
                ))
            
            logger.info(f"Created round {next_round_id} for auction {auction_address} on chain {chain_id}")
            
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
            
            logger.debug(f"Processing Take event: auction={auction_address[-8:]}, taker={taker[-8:]}, amount_taken={amount_taken}, amount_paid={amount_paid}")
            
            block = self.web3_connections[chain_id].eth.get_block(event['blockNumber'])
            timestamp_unix = block['timestamp']  # Unix timestamp
            # Convert to datetime for PostgreSQL timestamp with time zone
            import datetime
            timestamp = datetime.datetime.fromtimestamp(timestamp_unix, tz=datetime.timezone.utc)
            
            # Find the most recent round; do not require is_active
            with self.db_conn.cursor() as cursor:
                # Prefer a round whose from_token matches this take's from_token
                cursor.execute("""
                    SELECT round_id, from_token, kicked_at, total_takes
                    FROM rounds
                    WHERE LOWER(auction_address) = LOWER(%s) 
                      AND chain_id = %s 
                      AND LOWER(from_token) = LOWER(%s)
                    ORDER BY kicked_at DESC, round_id DESC
                    LIMIT 1
                """, (auction_address, chain_id, from_token))
                round_data = cursor.fetchone()
                
                if not round_data:
                    # Fallback to any most-recent round for this auction
                    cursor.execute("""
                        SELECT round_id, from_token, kicked_at, total_takes
                        FROM rounds
                        WHERE LOWER(auction_address) = LOWER(%s) 
                          AND chain_id = %s 
                        ORDER BY kicked_at DESC, round_id DESC
                        LIMIT 1
                    """, (auction_address, chain_id))
                    round_data = cursor.fetchone()
                
                if round_data:
                    round_id = round_data['round_id']
                    kicked_at = round_data['kicked_at']
                    total_takes = round_data['total_takes'] or 0
                    logger.debug(f"Using round {round_id} for {auction_address[-8:]}, current total_takes: {total_takes}")
                    take_seq = total_takes + 1
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
                    
                    # Handle negative values (can occur due to out-of-order event processing)
                    if seconds_from_start < 0:
                        logger.warning(f"⚠️  Negative seconds_from_start ({seconds_from_start}) for take {auction_address[-8:]}")
                        logger.warning(f"   timestamp_unix: {timestamp_unix}, kicked_at: {kicked_at}")
                        logger.warning(f"   This suggests out-of-order event processing or clock skew")
                        seconds_from_start = 0  # Default to 0 for negative values
                else:
                    # No round present; still record the take with round_id=0
                    round_id = 0
                    take_seq = 1
                    seconds_from_start = 0
                    logger.debug(f"No round found for {auction_address[-8:]}; recording take with round_id=0")
                
                # Create take ID
                take_id = f"{auction_address}-{round_id}-{take_seq}"
                
                # Calculate price (amount_paid / amount_taken)
                price = amount_paid if amount_taken == 0 else amount_paid // amount_taken
                
                # Get want_token for this auction first
                cursor.execute("""
                    SELECT want_token FROM auctions 
                    WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s
                """, (auction_address, chain_id))
                
                auction_data = cursor.fetchone()
                if not auction_data:
                    logger.error(f"❌ Auction {auction_address} not found in database for take processing")
                    return
                    
                want_token = auction_data['want_token']
                txn_hash = self._normalize_transaction_hash(event['transactionHash'])
                # Insert take record with better error handling
                try:
                    cursor.execute("""
                        INSERT INTO takes (
                            take_id, auction_address, chain_id, round_id, take_seq,
                            taker, from_token, to_token, amount_taken, amount_paid, price,
                            timestamp, seconds_from_round_start,
                            block_number, transaction_hash, log_index
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        take_id, auction_address, chain_id, round_id, take_seq,
                        taker, from_token, want_token, amount_taken, amount_paid, price, 
                        timestamp, seconds_from_start,
                        event['blockNumber'], txn_hash, event['logIndex']
                    ))
                    
                    logger.debug(f"Inserted take {take_id} into database")
                    
                except Exception as insert_error:
                    logger.error(f"❌ Failed to insert take into database: {insert_error}")
                    logger.error(f"Take data: {take_id}, {auction_address}, {chain_id}, {round_id}, {take_seq}")
                    raise
                
                # Update round statistics if the round exists
                try:
                    if round_id != 0:
                        cursor.execute("""
                            UPDATE rounds SET
                                total_takes = total_takes + 1,
                                total_volume_sold = COALESCE(total_volume_sold, 0) + %s,
                                available_amount = available_amount - %s
                            WHERE LOWER(auction_address) = LOWER(%s) AND chain_id = %s AND round_id = %s
                        """, (amount_taken, amount_taken, auction_address, chain_id, round_id))
                        if cursor.rowcount > 0:
                            logger.debug(f"Updated round {round_id} stats: +1 take, -{amount_taken} available")
                        else:
                            logger.debug(f"No existing round row to update for {auction_address[-8:]} round {round_id}")
                except Exception as update_error:
                    logger.error(f"❌ Failed to update round statistics: {update_error}")
                    # Do not raise; we already recorded the take
            
            logger.info(f"🎉 Successfully processed take {take_id} on chain {chain_id}")
            
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
    
    def _discover_and_store_token(self, token_address: str, chain_id: int) -> None:
        """Discover token metadata and store in database if not exists"""
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
                        logger.info(f"✅ Discovered token: {symbol} ({name}) at {token_address} on chain {chain_id}")
                    else:
                        logger.info(f"✅ Discovered token (partial metadata) at {token_address} on chain {chain_id}")
                
            except Exception as contract_error:
                logger.warning(f"Failed to process token contract {token_address}: {type(contract_error).__name__}: {contract_error}")
                # Store token with minimal info
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
            block = self.web3_connections[chain_id].eth.get_block(event['blockNumber'])
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
                    
        except Exception as e:
            logger.error(f"Failed to process auction enabled event: {e}")
    
    def _detect_takes_from_transfers(self, w3: Web3, chain_id: int, from_block: int, to_block: int) -> None:
        """Detect takes by monitoring Transfer events from auction contracts"""
        if chain_id not in self.tracked_auctions:
            return
        
        auction_addresses = list(self.tracked_auctions[chain_id].keys())
        if not auction_addresses:
            return
        
        # Process auctions in batches to avoid RPC query limits
        BATCH_SIZE = 20
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
            logger.info(f"🔍 Querying Transfer events for {len(auction_batch)} auctions in batch")
            
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
                logger.info(f"🎯 Found {len(logs)} Transfer events from {len(auction_batch)} auctions in blocks {from_block}-{to_block}")
                
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
        """Process a raw Transfer log from eth_getLogs"""
        try:
            # Decode the Transfer log
            # log.topics[0] = Transfer event signature
            # log.topics[1] = from address (padded, this is the auction address)
            # log.topics[2] = to address (padded, this is the taker)
            # log.data = amount (uint256)
            
            # Extract addresses from topics (remove padding)
            auction_address = '0x' + log['topics'][1].hex()[-40:]  # Last 20 bytes (40 hex chars)
            taker_address = '0x' + log['topics'][2].hex()[-40:]    # Last 20 bytes (40 hex chars)
            
            # Normalize addresses
            auction_address = self._normalize_address(auction_address)
            taker_address = self._normalize_address(taker_address)
            
            # Decode amount from data field
            amount_taken_raw = int(log['data'].hex(), 16)  # Convert hex data to integer
            
            # Token address is the contract that emitted the event
            token_address = self._normalize_address(log['address'])
            
            # Get token decimals for normalization
            token_decimals = self._get_token_decimals(w3, token_address)
            
            # Normalize amounts to human-readable format
            amount_taken = float(amount_taken_raw) / (10 ** token_decimals)
            amount_paid = amount_taken  # For now, assume 1:1 - we'll improve this later
            
            # Ensure transaction hash has 0x prefix
            tx_hash = log['transactionHash']
            if isinstance(tx_hash, bytes):
                tx_hash = '0x' + tx_hash.hex()
            elif not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            
            logger.debug(f"🔄 Processing raw Transfer: token={token_address[-8:]}, auction={auction_address[-8:]}, taker={taker_address[-8:]}, amount={amount_taken} (decimals={token_decimals})")
            
            # Create a synthetic Take event structure to reuse existing _process_take logic
            synthetic_take_event = {
                'args': {
                    'taker': taker_address,
                    'amountTaken': amount_taken,
                    'amountPaid': amount_paid,
                    'from': token_address
                },
                'blockNumber': log['blockNumber'],
                'transactionHash': tx_hash,
                'logIndex': log['logIndex']
            }
            
            # Use existing _process_take logic
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
    
    def _get_token_decimals(self, w3: Web3, token_address: str) -> int:
        """Get token decimals, with caching and fallback to 18"""
        # Check if we already know the decimals from database
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT decimals FROM tokens 
                    WHERE LOWER(address) = LOWER(%s)
                    LIMIT 1
                """, (token_address,))
                result = cursor.fetchone()
                if result and result['decimals'] is not None:
                    return result['decimals']
        except Exception as e:
            logger.debug(f"Could not fetch decimals from database for {token_address[-8:]}: {e}")
        
        # Try to call decimals() on the token contract
        try:
            erc20_abi = self.contract_abis.get('erc20', [])
            if erc20_abi:
                token_contract = w3.eth.contract(address=token_address, abi=erc20_abi)
                decimals = token_contract.functions.decimals().call()
                logger.debug(f"Fetched {decimals} decimals for token {token_address[-8:]}")
                return decimals
        except Exception as e:
            logger.debug(f"Could not call decimals() on token {token_address[-8:]}: {e}")
        
        # Fallback to 18 decimals (most common)
        logger.debug(f"Using fallback 18 decimals for token {token_address[-8:]}")
        return 18
    
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
        else:
            logger.info(f"Chain {chain_id} already has {len(self.tracked_auctions[chain_id])} tracked auctions")
        
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
        logger.info(f"Factory {factory_address} on chain {chain_id}: last_indexed_block={last_indexed_block}, current_block={current_block}")
        
        if last_indexed_block >= current_block:
            logger.debug(f"Factory {factory_address} on chain {chain_id} up to date at block {current_block}")
            return
        
        # Process in batches
        batch_size = self.config['indexer']['block_batch_size']
        from_block = last_indexed_block + 1
        
        logger.info(f"Processing factory {factory_address} on chain {chain_id} from block {from_block} to {current_block}")
        
        while from_block <= current_block:
            to_block = min(from_block + batch_size - 1, current_block)
            
            # Progress logging every 5000 blocks
            blocks_processed = to_block - last_indexed_block
            if blocks_processed > 0 and blocks_processed % 5000 < batch_size:
                remaining_blocks = current_block - to_block
                logger.info(f"🔄 Progress: Factory {factory_address[:4]}..{factory_address[-4:]} processed {blocks_processed:,} blocks, {remaining_blocks:,} remaining (at block {to_block:,})")
            
            try:
                # Process factory events for this specific factory
                self._process_factory_events(
                    w3, chain_id, factory_config, from_block, to_block
                )
                
                # Process auction events for tracked auctions on this chain
                self._process_auction_events(w3, chain_id, from_block, to_block)
                
                # Update progress for this specific factory
                self._update_last_indexed_block(chain_id, factory_address, to_block)
                logger.debug(f"Factory {factory_address} on chain {chain_id} processed blocks {from_block} to {to_block}")
                
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
            logger.debug(f"Querying {factory_type} factory {factory_address[-8:]} events from blocks {from_block}-{to_block}")
            event_cls = factory_contract.events.DeployedNewAuction
            events = self._get_event_logs_with_split(event_cls, from_block, to_block)
            if events:
                logger.info(f"🎉 Found {len(events)} auction deployment events in blocks {from_block}-{to_block}")
            
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

        # Since Take events don't actually exist, detect all takes via Transfer events
        logger.debug(f"Running Transfer event detection for takes on chain {chain_id} for blocks {from_block}-{to_block}")
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
                    logger.info(f"Creating {contract_type} contract for auction {address[-8:]} on chain {chain_id}")
                    
                    try:
                        contract = self._get_contract_instance(w3, address, contract_type)
                        
                        # Debug: Check what events are available
                        logger.info(f"Contract {address[-8:]} events: {list(contract.events.__dict__.keys())}")
                        
                        self.tracked_auctions[chain_id][address] = contract
                        logger.info(f"Successfully added auction {address[-8:]} to tracked auctions for chain {chain_id}")
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
        
        logger.info(f"Starting indexer for networks: {', '.join(networks)}")
        
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
                
                logger.debug(f"Sleeping for {poll_interval} seconds...")
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Indexer stopped by user")
        except Exception as e:
            logger.error(f"Indexer error: {e}")
            raise


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
