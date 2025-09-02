#!/usr/bin/env python3
"""
Clean up spam tokens from the database
Goes through all tokens, checks if they are spam, and deletes related records
"""

import os
import sys
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SpamTokenCleanup:
    def __init__(self):
        self.db_conn = None
        self.web3_conn = None
        self.contract_abis = {}
        
    def connect_database(self):
        """Connect to PostgreSQL database"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL not found in environment")
            sys.exit(1)
            
        try:
            self.db_conn = psycopg2.connect(
                database_url,
                cursor_factory=RealDictCursor
            )
            self.db_conn.autocommit = False  # Use transactions
            logger.info("✅ Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def connect_web3(self):
        """Connect to Ethereum mainnet for token checks"""
        rpc_url = os.getenv('ETHEREUM_RPC_URL', 'http://localhost:8545')  # Default to local for dev
        try:
            self.web3_conn = Web3(Web3.HTTPProvider(rpc_url))
            if not self.web3_conn.is_connected():
                logger.error("Failed to connect to Web3")
                sys.exit(1)
            logger.info(f"✅ Connected to Web3 at {rpc_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Web3: {e}")
            sys.exit(1)
    
    def load_erc20_abi(self):
        """Load ERC20 ABI"""
        # Standard ERC20 ABI subset for totalSupply and symbol
        erc20_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }
        ]
        self.contract_abis['erc20'] = erc20_abi
        logger.info("✅ Loaded ERC20 ABI")
    
    def is_spam_token(self, token_address: str, symbol: str = None) -> bool:
        """Check if a token is likely spam based on heuristics"""
        try:
            # Check if symbol is 'ERC20' (common spam indicator)
            if symbol == 'ERC20':
                logger.debug(f"Token {token_address} detected as spam: symbol is 'ERC20'")
                return True
            
            # Check if totalSupply > 2^150
            try:
                token_contract = self.web3_conn.eth.contract(
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
    
    def get_all_tokens(self):
        """Get all unique tokens from the database (both tokens table and price_requests)"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get tokens from tokens table
                cursor.execute("""
                    SELECT DISTINCT address, symbol, name, chain_id
                    FROM tokens
                    WHERE chain_id = 1  -- Only check mainnet tokens
                    ORDER BY address
                """)
                tokens_from_table = cursor.fetchall()
                
                # Get tokens from price_requests that aren't in tokens table
                cursor.execute("""
                    SELECT DISTINCT pr.token_address as address, NULL as symbol, NULL as name, pr.chain_id
                    FROM price_requests pr
                    LEFT JOIN tokens t ON LOWER(pr.token_address) = LOWER(t.address) AND pr.chain_id = t.chain_id
                    WHERE pr.chain_id = 1 AND t.address IS NULL
                    ORDER BY pr.token_address
                """)
                tokens_from_requests = cursor.fetchall()
                
                # Combine both lists
                all_tokens = list(tokens_from_table) + list(tokens_from_requests)
                logger.info(f"Found {len(tokens_from_table)} tokens in tokens table and {len(tokens_from_requests)} additional tokens in price_requests")
                logger.info(f"Total: {len(all_tokens)} unique mainnet tokens to check")
                return all_tokens
        except Exception as e:
            logger.error(f"Failed to get tokens: {e}")
            return []
    
    def delete_token_records(self, token_address: str, chain_id: int) -> dict:
        """Delete all records for a spam token"""
        deleted_counts = {
            'price_requests': 0,
            'token_prices': 0,
            'tokens': 0
        }
        
        try:
            with self.db_conn.cursor() as cursor:
                # Delete from price_requests
                cursor.execute("""
                    DELETE FROM price_requests 
                    WHERE LOWER(token_address) = LOWER(%s) AND chain_id = %s
                """, (token_address, chain_id))
                deleted_counts['price_requests'] = cursor.rowcount
                
                # Check if token_prices table exists and delete from it
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'token_prices'
                    )
                """)
                if cursor.fetchone()['exists']:
                    cursor.execute("""
                        DELETE FROM token_prices 
                        WHERE LOWER(token_address) = LOWER(%s) AND chain_id = %s
                    """, (token_address, chain_id))
                    deleted_counts['token_prices'] = cursor.rowcount
                
                # Delete from tokens
                cursor.execute("""
                    DELETE FROM tokens 
                    WHERE LOWER(address) = LOWER(%s) AND chain_id = %s
                """, (token_address, chain_id))
                deleted_counts['tokens'] = cursor.rowcount
                
        except Exception as e:
            logger.error(f"Failed to delete records for token {token_address}: {e}")
            raise
        
        return deleted_counts
    
    def cleanup_spam_tokens(self):
        """Main cleanup process"""
        logger.info("🧹 Starting spam token cleanup...")
        
        tokens = self.get_all_tokens()
        if not tokens:
            logger.info("No tokens to check")
            return
        
        spam_count = 0
        total_deleted = {
            'price_requests': 0,
            'token_prices': 0,
            'tokens': 0
        }
        
        for token in tokens:
            try:
                address = token['address']
                symbol = token['symbol']
                chain_id = token['chain_id']
                
                logger.debug(f"Checking token {address} (symbol: {symbol})")
                
                if self.is_spam_token(address, symbol):
                    logger.info(f"🚫 Found spam token: {address} (symbol: {symbol})")
                    
                    # Start transaction
                    with self.db_conn:
                        deleted = self.delete_token_records(address, chain_id)
                        
                        # Update totals
                        for key in total_deleted:
                            total_deleted[key] += deleted[key]
                        
                        spam_count += 1
                        logger.info(f"✅ Deleted spam token {address}: "
                                  f"price_requests={deleted['price_requests']}, "
                                  f"token_prices={deleted['token_prices']}, "
                                  f"tokens={deleted['tokens']}")
                
            except Exception as e:
                logger.error(f"Error processing token {token.get('address', 'unknown')}: {e}")
                # Rollback this token's transaction
                self.db_conn.rollback()
                continue
        
        logger.info(f"🎉 Cleanup complete!")
        logger.info(f"   Spam tokens removed: {spam_count}")
        logger.info(f"   Total records deleted:")
        logger.info(f"     - price_requests: {total_deleted['price_requests']}")
        logger.info(f"     - token_prices: {total_deleted['token_prices']}")
        logger.info(f"     - tokens: {total_deleted['tokens']}")
    
    def run(self):
        """Run the cleanup process"""
        self.connect_database()
        self.connect_web3()
        self.load_erc20_abi()
        
        try:
            self.cleanup_spam_tokens()
        finally:
            if self.db_conn:
                self.db_conn.close()
                logger.info("Database connection closed")

if __name__ == "__main__":
    cleanup = SpamTokenCleanup()
    cleanup.run()