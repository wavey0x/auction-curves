#!/usr/bin/env python3
"""
CowSwap Price Service
Polls for recent takes and fetches current token prices from CowSwap API (mainnet only)
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

class CowSwapPriceService:
    """Price service using CowSwap API to fetch current token prices (mainnet only)"""
    
    def __init__(self, poll_interval: int = 6, recency_blocks: int = 40, once: bool = False):
        self.db_conn = None
        self.poll_interval = max(1, int(poll_interval))
        self.recency_blocks = recency_blocks
        self.once = once
        self.base_url = "https://api.cow.fi/mainnet/api/v1/token"
        self.mainnet_chain_id = 1  # CowSwap only supports mainnet
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
    
    def get_recent_mainnet_takes(self) -> List[Dict]:
        """Get recent takes from mainnet only"""
        try:
            with self.db_conn.cursor() as cursor:
                # Get recent takes from mainnet only
                cursor.execute("""
                    WITH latest_block AS (
                        SELECT MAX(block_number) as max_block
                        FROM takes
                        WHERE chain_id = %s
                    )
                    SELECT t.*, lb.max_block
                    FROM takes t
                    CROSS JOIN latest_block lb
                    WHERE t.chain_id = %s
                      AND t.block_number > lb.max_block - %s
                      
                    ORDER BY t.timestamp DESC
                    LIMIT 100
                """, (self.mainnet_chain_id, self.mainnet_chain_id, self.recency_blocks))
                
                takes = cursor.fetchall()
                
                # Filter out already processed takes
                new_takes = [t for t in takes if t['take_id'] not in self.processed_takes]
                
                if new_takes:
                    logger.info(f"[COWSWAP] Found {len(new_takes)} recent unprocessed mainnet takes (< {self.recency_blocks} blocks old)")
                
                return new_takes
                
        except Exception as e:
            logger.error(f"Failed to get recent mainnet takes: {e}")
            return []
    
    def get_token_price_via_quote(self, token_address: str) -> Optional[Decimal]:
        """Get token price by requesting a quote against USDC"""
        usdc_address = "0xA0b86a33E6a42Fa1e4119c88fc3A2Ef3E7cae1c0"  # USDC mainnet
        # Use a realistic whale address that likely has tokens
        whale_address = "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503"  # Binance hot wallet
        
        # Try different sell amounts to account for different token decimals and liquidity
        sell_amounts = [
            "100000000000000000",    # 0.1 token (18 decimals) - smaller amount for expensive tokens
            "1000000000000000000",   # 1 token (18 decimals) 
            "1000000",               # 1 token (6 decimals) for USDC-like tokens
        ]
        
        for sell_amount in sell_amounts:
            try:
                quote_params = {
                    "from": whale_address,
                    "receiver": whale_address,  # Required parameter
                    "sellToken": token_address,
                    "buyToken": usdc_address,
                    "kind": "sell",
                    "sellAmountBeforeFee": sell_amount,
                    "partiallyFillable": False
                }
                
                url = "https://api.cow.fi/mainnet/api/v1/quote"
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'price-service/1.0'
                }
                
                logger.info(f"[COWSWAP] 📤 Requesting quote for {token_address[:6]}..{token_address[-4:]} (amount: {sell_amount})")
                
                response = requests.post(url, json=quote_params, headers=headers, timeout=10)
                logger.info(f"[COWSWAP] 📥 Response: {response.status_code}")
                
                if response.status_code == 200:
                    quote = response.json()
                    # Calculate price: buyAmountAfterFee / sellAmountBeforeFee * (USDC price ~ $1)
                    buy_amount = float(quote.get("buyAmountAfterFee", 0))
                    actual_sell_amount = float(quote.get("sellAmountBeforeFee", sell_amount))
                    
                    if buy_amount > 0 and actual_sell_amount > 0:
                        # Convert to price per token (assuming USDC = $1, 6 decimals)
                        # Normalize based on actual decimals - assume sell token has 18 decimals, USDC has 6
                        price_usd = (buy_amount / 1e6) / (actual_sell_amount / 1e18)
                        logger.info(f"[COWSWAP] 💰 Quote price for {token_address[:6]}..{token_address[-4:]}: ${price_usd:.6f}")
                        return Decimal(str(price_usd))
                    else:
                        logger.debug(f"[COWSWAP] ⚠️ Invalid quote amounts for {token_address[:6]}..{token_address[-4:]}")
                        continue  # Try next sell amount
                        
                elif response.status_code == 400:
                    try:
                        error_detail = response.text
                        logger.debug(f"[COWSWAP] ⚠️ 400 Bad Request for {token_address[:6]}..{token_address[-4:]} (amount: {sell_amount}): {error_detail}")
                    except:
                        logger.debug(f"[COWSWAP] ⚠️ 400 Bad Request for {token_address[:6]}..{token_address[-4:]} with amount {sell_amount}")
                    continue  # Try next sell amount
                elif response.status_code == 403:
                    logger.error(f"[COWSWAP] ❌ 403 FORBIDDEN for {token_address[:6]}..{token_address[-4:]}")
                    return None  # Don't try other amounts if blocked
                elif response.status_code == 404:
                    try:
                        error_detail = response.text
                        logger.debug(f"[COWSWAP] ⚠️ 404 for {token_address[:6]}..{token_address[-4:]} (amount: {sell_amount}): {error_detail}")
                    except:
                        logger.debug(f"[COWSWAP] ⚠️ 404 for {token_address[:6]}..{token_address[-4:]} with amount {sell_amount}")
                    continue  # Try next sell amount
                else:
                    try:
                        error_detail = response.text
                        logger.error(f"[COWSWAP] ❌ Quote API error {response.status_code} for {token_address[:6]}..{token_address[-4:]}: {error_detail}")
                    except:
                        logger.error(f"[COWSWAP] ❌ Quote API error {response.status_code} for {token_address[:6]}..{token_address[-4:]}")
                    continue  # Try next sell amount
                    
            except Exception as e:
                logger.error(f"[COWSWAP] ❌ Quote request failed for {token_address[:6]}..{token_address[-4:]}: {e}")
                continue  # Try next sell amount
        
        # If we get here, none of the sell amounts worked
        logger.debug(f"[COWSWAP] ❌ All quote attempts failed for {token_address[:6]}..{token_address[-4:]}")
        return None

    def fetch_token_prices(self, token_addresses: List[str]) -> Dict[str, Optional[Decimal]]:
        """Fetch current prices for multiple tokens using CowSwap quote API"""
        prices = {}
        
        logger.info(f"[COWSWAP] 🔍 Fetching prices for {len(token_addresses)} tokens via quotes")
        logger.info(f"[COWSWAP] ⏰ Using 30-second delays between requests to avoid rate limiting")
        
        for i, token_address in enumerate(token_addresses):
            if i > 0:
                logger.info(f"[COWSWAP] 💤 Waiting 30 seconds before next request ({i+1}/{len(token_addresses)})...")
                time.sleep(30)
            
            logger.info(f"[COWSWAP] 🚀 Processing token {i+1}/{len(token_addresses)}: {token_address[:6]}..{token_address[-4:]}")
            price = self.get_token_price_via_quote(token_address)
            prices[token_address] = price
            
            if price:
                logger.info(f"[COWSWAP] ✅ Got price for {token_address[:6]}..{token_address[-4:]}: ${price:.4f}")
            else:
                logger.info(f"[COWSWAP] ❌ No price for {token_address[:6]}..{token_address[-4:]}")
        
        successful_prices = len([p for p in prices.values() if p is not None])
        logger.info(f"[COWSWAP] 📊 Successfully got {successful_prices}/{len(token_addresses)} prices")
        return prices
    
    def store_price(self, token_address: str, price_usd: Decimal, block_number: int) -> None:
        """Store token price in database"""
        try:
            with self.db_conn.cursor() as cursor:
                # Store with current timestamp since CowSwap provides current prices
                cursor.execute("""
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address, 
                        price_usd, timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, 'cowswap', NOW())
                """, (
                    self.mainnet_chain_id,
                    block_number,  # Store the block from the take for reference
                    token_address, 
                    price_usd,
                    int(time.time())  # Current timestamp
                ))
                
                if cursor.rowcount > 0:
                    logger.info(f"[COWSWAP] 💰 Stored price: {token_address[:6]}..{token_address[-4:]} = ${price_usd:.4f}")
                    
        except Exception as e:
            logger.error(f"Failed to store price for {token_address}: {e}")
    
    def process_takes_batch(self, takes: List[Dict]) -> None:
        """Process a batch of takes and fetch prices for all their tokens"""
        if not takes:
            return
            
        try:
            # Collect all unique tokens from the takes
            all_tokens = set()
            take_tokens = {}  # take_id -> (from_token, want_token, block_number)
            
            for take in takes:
                take_id = take['take_id']
                from_token = take['from_token']
                want_token = take['to_token']  # Column name is 'to_token' in database
                block_number = take['block_number']
                
                all_tokens.add(from_token)
                all_tokens.add(want_token)
                take_tokens[take_id] = (from_token, want_token, block_number)
            
            logger.info(f"[COWSWAP] Processing {len(takes)} takes with {len(all_tokens)} unique tokens")
            
            # Fetch prices for all tokens
            token_prices = self.fetch_token_prices(list(all_tokens))
            
            # Store prices and mark takes as processed
            prices_stored = 0
            for take_id, (from_token, want_token, block_number) in take_tokens.items():
                # Store price for from_token if available
                if from_token in token_prices and token_prices[from_token] is not None:
                    self.store_price(from_token, token_prices[from_token], block_number)
                    prices_stored += 1
                
                # Store price for want_token if available  
                if want_token in token_prices and token_prices[want_token] is not None:
                    self.store_price(want_token, token_prices[want_token], block_number)
                    prices_stored += 1
                
                # Mark take as processed
                self.processed_takes.add(take_id)
            
            logger.info(f"[COWSWAP] ✅ Processed {len(takes)} takes: stored {prices_stored} prices")
                
        except Exception as e:
            logger.error(f"[COWSWAP] ❌ Failed to process takes batch: {e}")
    
    def run_polling_loop(self) -> None:
        """Main polling loop"""
        logger.info("🚀 Starting CowSwap Price Service")
        logger.info(f"📊 Settings: poll_interval={self.poll_interval}s, recency_blocks={self.recency_blocks}")
        logger.info("🌐 CowSwap API supports mainnet (chain_id=1) only")
        
        while True:
            try:
                # Get recent mainnet takes
                recent_takes = self.get_recent_mainnet_takes()
                
                if recent_takes:
                    # Process takes in batch for efficiency
                    self.process_takes_batch(recent_takes)
                else:
                    logger.debug(f"[COWSWAP] No new recent mainnet takes found")
                
                if self.once:
                    logger.info("✅ Single cycle completed (--once mode)")
                    break
                
                # Wait before next poll
                logger.debug(f"[COWSWAP] Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping CowSwap price service...")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                if not self.once:
                    time.sleep(self.poll_interval)
                else:
                    break

def main():
    parser = argparse.ArgumentParser(description='CowSwap Price Service')
    parser.add_argument('--poll-interval', type=int, default=10, 
                       help='Poll interval in seconds (default: 10)')
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
    
    service = CowSwapPriceService(
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