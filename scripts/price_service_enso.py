#!/usr/bin/env python3
"""
ENSO Price Service
Polls for recent takes and fetches current token prices from ENSO API
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

class EnsoAPIError(Exception):
    """Custom exception for ENSO API errors"""
    pass

class EnsoPriceService:
    """Price service using ENSO API to fetch current token prices"""
    
    def __init__(self, poll_interval: int = 10, recency_minutes: int = None, once: bool = False):
        self.db_conn = None
        self.poll_interval = max(1, int(poll_interval))
        
        # Use environment-specific max age configuration if recency_minutes not provided
        if recency_minutes is None:
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            env_key = f"{app_mode.upper()}_QUOTE_API_MAX_AGE_MINUTES"
            self.recency_minutes = int(os.getenv(env_key, '10'))
        else:
            self.recency_minutes = recency_minutes
            
        self.once = once
        self.base_url = "https://api.enso.finance/api/v1/shortcuts/route"
        
        # Supported chains and their parameters
        self.chain_configs = {
            1: {
                "name": "Mainnet",
                "usdc": "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI (more liquid)
                "whale": "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503"  # Binance hot wallet
            },
            137: {
                "name": "Polygon", 
                "usdc": "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
                "whale": "0x1a1ec25DC08e98e5E93F1104B5e5cfD298707d31"  # Binance Polygon
            },
            42161: {
                "name": "Arbitrum",
                "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                "whale": "0x489ee077994B6658eAfA855C308275EAd8097C4A"  # Binance Arbitrum
            },
            10: {
                "name": "Optimism",
                "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
                "whale": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58"  # Optimism Gateway
            },
            8453: {
                "name": "Base",
                "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "whale": "0x4C80E24119CFB836cdF0a6b53dc23F04F7e652CA"  # Coinbase hot wallet
            }
        }
        
        # Removed processed_takes tracking - now using database status
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize database connection"""
        try:
            # Use the same database URL as other services
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
            logger.info("✅ Database connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)
    
    def get_fresh_price_requests(self) -> List[Dict]:
        """Get recent price requests that are within recency window and not processed yet"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get current time for freshness check
                current_time = int(time.time())
                
                # Select pending requests that are fresh enough for quote APIs
                cursor.execute("""
                    SELECT pr.id, pr.chain_id, pr.block_number, pr.token_address, 
                           pr.request_type, pr.auction_address, pr.round_id, pr.txn_timestamp
                    FROM price_requests pr
                    WHERE pr.status = 'pending'
                      AND pr.chain_id IN %s
                      AND pr.txn_timestamp IS NOT NULL
                      AND (%s - pr.txn_timestamp) <= %s  -- Within recency window (seconds)
                    ORDER BY pr.txn_timestamp DESC
                    LIMIT 100
                """, (
                    tuple(self.chain_configs.keys()),
                    current_time,
                    self.recency_minutes * 60
                ))
                
                requests = cursor.fetchall()
                
                if requests:
                    logger.info(f"[ENSO] Found {len(requests)} fresh price requests (< {self.recency_minutes} minutes old)")
                
                return requests
                
        except Exception as e:
            logger.error(f"Failed to get fresh price requests: {e}")
            return []
    
    def get_token_price_via_route(self, token_address: str, chain_id: int) -> Optional[Decimal]:
        """Get token price by requesting a route quote against stablecoin (DAI/USDC)"""
        if chain_id not in self.chain_configs:
            logger.debug(f"Chain {chain_id} not supported by ENSO")
            return None
            
        # Skip ETH - only ypricemagic should handle ETH pricing
        if token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
            logger.debug(f"Skipping ETH price request - handled by ypricemagic only")
            return None
            
        config = self.chain_configs[chain_id]
        usdc_address = config["usdc"]
        whale_address = config["whale"]
        
        # Try different sell amounts to account for different token decimals and liquidity
        sell_amounts = [
            "100000000000000000",    # 0.1 token (18 decimals)
            "1000000000000000000",   # 1 token (18 decimals) 
            "10000000000000000000",  # 10 tokens (18 decimals)
            "1000000",               # 1 token (6 decimals) for USDC-like tokens
        ]
        
        for sell_amount in sell_amounts:
            try:
                params = {
                    "fromAddress": whale_address,
                    "amountIn": sell_amount,
                    "tokenIn": token_address,
                    "tokenOut": usdc_address,
                    "chainId": str(chain_id),
                    "routingStrategy": "router"
                }
                
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'auction-price-service/1.0'
                }
                
                logger.debug(f"[ENSO] 📤 Requesting route for {token_address[:6]}..{token_address[-4:]} on {config['name']} (amount: {sell_amount})")
                
                response = requests.get(self.base_url, params=params, headers=headers, timeout=15)
                logger.debug(f"[ENSO] 📥 Response: {response.status_code}")
                
                if response.status_code == 200:
                    route_data = response.json()
                    
                    # Extract price from route response
                    amount_out = route_data.get("amountOut")
                    if amount_out:
                        amount_out_int = int(amount_out)
                        amount_in_int = int(sell_amount)
                        
                        if amount_out_int > 0 and amount_in_int > 0:
                            # Calculate price: amountOut (DAI, 18 decimals) / amountIn (token, assume 18 decimals)
                            # Normalize: (amountOut / 1e18) / (amountIn / 1e18) = amountOut / amountIn
                            price_usd = amount_out_int / amount_in_int
                            logger.info(f"[ENSO] 💰 Route price for {token_address[:6]}..{token_address[-4:]} on {config['name']}: ${price_usd:.6f}")
                            return Decimal(str(price_usd))
                        else:
                            logger.debug(f"[ENSO] ⚠️ Invalid route amounts for {token_address[:6]}..{token_address[-4:]}")
                            continue  # Try next sell amount
                            
                elif response.status_code == 400:
                    try:
                        error_detail = response.text
                        logger.debug(f"[ENSO] ⚠️ 400 Bad Request for {token_address[:6]}..{token_address[-4:]} (amount: {sell_amount}): {error_detail}")
                    except:
                        logger.debug(f"[ENSO] ⚠️ 400 Bad Request for {token_address[:6]}..{token_address[-4:]} with amount {sell_amount}")
                    continue  # Try next sell amount
                    
                elif response.status_code == 429:
                    logger.warning(f"[ENSO] ⚠️ Rate limit hit for {token_address[:6]}..{token_address[-4:]}, waiting 5 seconds...")
                    time.sleep(5)
                    continue  # Try next sell amount after delay
                    
                else:
                    try:
                        error_detail = response.text
                        logger.error(f"[ENSO] ❌ Route API error {response.status_code} for {token_address[:6]}..{token_address[-4:]}: {error_detail}")
                    except:
                        logger.error(f"[ENSO] ❌ Route API error {response.status_code} for {token_address[:6]}..{token_address[-4:]}")
                    continue  # Try next sell amount
                    
            except Exception as e:
                logger.error(f"[ENSO] ❌ Route request failed for {token_address[:6]}..{token_address[-4:]}: {e}")
                continue  # Try next sell amount
        
        # If we get here, none of the sell amounts worked
        logger.debug(f"[ENSO] ❌ All route attempts failed for {token_address[:6]}..{token_address[-4:]}")
        return None
    
    def store_price(self, chain_id: int, token_address: str, price_usd: Decimal, block_number: int, txn_timestamp: int = None) -> None:
        """Store token price in database with transaction timestamp"""
        try:
            with self.db_conn.cursor() as cursor:
                # Store with current timestamp since ENSO provides current prices
                cursor.execute("""
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address, 
                        price_usd, timestamp, txn_timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'enso', NOW())
                """, (
                    chain_id, 
                    block_number,  # Store the block from the price request
                    token_address, 
                    price_usd,
                    int(time.time()),  # Current timestamp for when price was fetched
                    txn_timestamp  # Original transaction timestamp
                ))
                
                if cursor.rowcount > 0:
                    chain_name = self.chain_configs.get(chain_id, {}).get("name", f"Chain{chain_id}")
                    logger.info(f"[ENSO] 💰 Stored price: {token_address[:6]}..{token_address[-4:]} on {chain_name} = ${price_usd:.4f}")
                    
        except Exception as e:
            logger.error(f"Failed to store price for {token_address}: {e}")
    
    def mark_request_completed(self, request_id: int) -> None:
        """Mark a price request as completed"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'completed', processed_at = NOW() 
                    WHERE id = %s
                """, (request_id,))
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as completed: {e}")
    
    def mark_request_failed(self, request_id: int, error_message: str) -> None:
        """Mark a price request as failed"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE price_requests 
                    SET status = 'failed', error_message = %s, processed_at = NOW(),
                        retry_count = retry_count + 1
                    WHERE id = %s
                """, (error_message[:500], request_id))  # Truncate error message
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as failed: {e}")
    
    def process_price_request(self, request: Dict) -> None:
        """Process a single price request"""
        try:
            request_id = request['id']
            chain_id = request['chain_id']
            token_address = request['token_address']
            block_number = request['block_number']
            txn_timestamp = request['txn_timestamp']
            
            chain_name = self.chain_configs.get(chain_id, {}).get("name", f"Chain{chain_id}")
            logger.debug(f"Processing request {request_id} for token {token_address[:6]}..{token_address[-4:]} on {chain_name}")
            
            # Fetch price for the token
            price = self.get_token_price_via_route(token_address, chain_id)
            
            if price is not None:
                # Store price with transaction timestamp
                self.store_price(chain_id, token_address, price, block_number, txn_timestamp)
                # Mark request as completed
                self.mark_request_completed(request_id)
                logger.info(f"[ENSO] ✅ Completed request {request_id}: {token_address[:6]}..{token_address[-4:]} = ${price:.4f}")
            else:
                # Mark request as failed
                self.mark_request_failed(request_id, "Failed to fetch price from ENSO API")
                logger.warning(f"[ENSO] ❌ Failed request {request_id}: No price available for {token_address[:6]}..{token_address[-4:]}")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to process price request {request.get('id', 'unknown')}: {e}")
            # Mark as failed if we have the request_id
            if 'id' in request:
                self.mark_request_failed(request['id'], str(e))
    
    def run_polling_loop(self) -> None:
        """Main polling loop"""
        logger.info("🚀 Starting ENSO Price Service")
        logger.info(f"📊 Settings: poll_interval={self.poll_interval}s, recency_minutes={self.recency_minutes}")
        chain_list = [f'{cfg["name"]} (chain {cid})' for cid, cfg in self.chain_configs.items()]
        logger.info(f"🌐 ENSO API supports: {', '.join(chain_list)}")
        
        while True:
            try:
                # Get fresh price requests within recency window
                fresh_requests = self.get_fresh_price_requests()
                
                if fresh_requests:
                    for request in fresh_requests:
                        self.process_price_request(request)
                        # Small delay between requests to avoid rate limits
                        time.sleep(0.5)
                else:
                    logger.debug(f"[ENSO] No fresh price requests found (within {self.recency_minutes} minutes)")
                
                if self.once:
                    logger.info("✅ Single cycle completed (--once mode)")
                    break
                
                # Wait before next poll
                logger.debug(f"[ENSO] Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping ENSO price service...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                if not self.once:
                    time.sleep(self.poll_interval)
                else:
                    break

def main():
    parser = argparse.ArgumentParser(description='ENSO Price Service')
    parser.add_argument('--poll-interval', type=int, default=10, 
                       help='Poll interval in seconds (default: 10)')
    parser.add_argument('--recency-minutes', type=int, default=10,
                       help='How recent takes must be in minutes (default: 10)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    service = EnsoPriceService(
        poll_interval=args.poll_interval,
        recency_minutes=args.recency_minutes,
        once=args.once
    )
    
    try:
        service.run_polling_loop()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()