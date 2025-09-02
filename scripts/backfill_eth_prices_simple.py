#!/usr/bin/env python3
"""
Simple ETH Price Backfill Script
Fetches ETH prices for all take blocks using ypricemagic and stores them directly.
Run with: brownie run backfill_eth_prices_simple --network mainnet
"""

import os
import sys
import time
import psycopg2
import psycopg2.extras
from decimal import Decimal
from brownie import web3
from y import magic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Simple ETH price backfill using ypricemagic"""
    
    print("🚀 Starting ETH Price Backfill")
    
    # Database connection
    app_mode = os.getenv('APP_MODE', 'dev').lower()
    if app_mode == 'dev':
        db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5433/auction_dev')
    else:
        db_url = os.getenv('PROD_DATABASE_URL')
        
    if not db_url:
        print("❌ No database URL configured")
        return
        
    try:
        db_conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        db_conn.autocommit = True
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # ETH address
    eth_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
    
    # Get missing ETH price blocks
    try:
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT t.chain_id, t.block_number
                FROM takes t
                LEFT JOIN token_prices tp ON (
                    tp.chain_id = t.chain_id 
                    AND tp.block_number = t.block_number 
                    AND tp.token_address = %s
                    AND tp.source = 'ypricemagic'
                )
                WHERE t.chain_id = 1  -- Only mainnet
                  AND tp.id IS NULL  -- No ETH price exists
                ORDER BY t.block_number
            """, (eth_address,))
            
            missing_blocks = cursor.fetchall()
            
    except Exception as e:
        print(f"❌ Failed to get missing blocks: {e}")
        return
    
    if not missing_blocks:
        print("✅ No missing ETH prices - all blocks already have ETH prices!")
        return
    
    print(f"📊 Found {len(missing_blocks)} blocks missing ETH prices")
    print("🔄 Starting price fetching...")
    
    # Process blocks
    success_count = 0
    failure_count = 0
    block_cache = {}
    
    for i, block_info in enumerate(missing_blocks, 1):
        block_number = block_info['block_number']
        
        if i % 50 == 0:
            print(f"Progress: {i}/{len(missing_blocks)} blocks ({success_count} success, {failure_count} failed)")
        
        try:
            # Fetch ETH price using ypricemagic
            price_raw = magic.get_price(eth_address, block=block_number, sync=True)
            
            if price_raw is None:
                print(f"❌ Block {block_number}: Price is None")
                failure_count += 1
                continue
                
            # Convert price to Decimal with proper error handling
            try:
                # Debug: show what we're getting from ypricemagic
                if failure_count < 3:  # Only show first few for debugging
                    print(f"🔍 Block {block_number}: Raw price = {price_raw} (type: {type(price_raw)})")
                
                if hasattr(price_raw, 'item'):  # numpy types
                    price_value = float(price_raw.item())
                elif isinstance(price_raw, (int, float)):
                    price_value = float(price_raw)
                else:
                    # Try to convert whatever it is to float first
                    price_value = float(price_raw)
                
                if price_value <= 0:
                    print(f"❌ Block {block_number}: Invalid price {price_value}")
                    failure_count += 1
                    continue
                    
                price = Decimal(str(price_value))
                
            except (ValueError, TypeError, Exception) as conversion_error:
                print(f"❌ Block {block_number}: Failed to convert price {price_raw} (type: {type(price_raw)}) - {conversion_error}")
                failure_count += 1
                continue
                
            # Get block timestamp (with caching)
            if block_number in block_cache:
                timestamp = block_cache[block_number]
            else:
                try:
                    block_info = web3.eth.get_block(block_number)
                    timestamp = block_info['timestamp']
                    
                    # Simple cache limit
                    if len(block_cache) >= 1000:
                        oldest_key = next(iter(block_cache))
                        del block_cache[oldest_key]
                    
                    block_cache[block_number] = timestamp
                    
                except Exception as block_error:
                    print(f"❌ Block {block_number}: Failed to get timestamp - {block_error}")
                    failure_count += 1
                    continue
            
            # Store price in database
            try:
                with db_conn.cursor() as cursor:
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
                        1,  # chain_id (mainnet)
                        block_number, 
                        eth_address,
                        Decimal(str(price)), 
                        timestamp
                    ))
                    
                    success_count += 1
                    
            except Exception as store_error:
                print(f"❌ Block {block_number}: Failed to store price - {store_error}")
                failure_count += 1
                continue
                
        except Exception as fetch_error:
            print(f"❌ Block {block_number}: Failed to fetch price - {fetch_error}")
            failure_count += 1
            continue
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.1)
    
    # Final summary
    print(f"\n✅ ETH Price Backfill Complete!")
    print(f"📊 Summary:")
    print(f"   • Blocks processed: {len(missing_blocks)}")
    print(f"   • Successful: {success_count}")
    print(f"   • Failed: {failure_count}")
    
    if success_count > 0:
        success_rate = (success_count / len(missing_blocks)) * 100
        print(f"   • Success rate: {success_rate:.1f}%")
        print(f"\n🎉 Added {success_count} ETH prices to the database!")
    
    db_conn.close()