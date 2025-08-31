#!/usr/bin/env python3
"""
Create a Take transaction on an auction with available tokens
"""
from brownie import accounts, LegacyAuction, Auction, MockERC20Enhanced
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    # Load deployment info  
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)

    # Use accounts
    deployer = accounts[0]
    taker = accounts[3]  # Different taker

    print("🎯 Creating Take transaction on auction with available tokens...")

    # Query database to find an auction with available tokens
    conn = psycopg2.connect("postgresql://postgres@localhost:5432/auction_dev")
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT ar.auction_address, ar.from_token, ar.initial_available,
                   a.want_token, a.version
            FROM rounds ar
            JOIN auctions a ON ar.auction_address = a.auction_address 
                            AND ar.chain_id = a.chain_id
            WHERE ar.initial_available > 0 
              AND ar.is_active = true
              AND ar.chain_id = 31337
            ORDER BY ar.initial_available DESC
            LIMIT 1
        """)
        
        auction_info = cursor.fetchone()
        if not auction_info:
            print("❌ No auctions with available tokens found")
            return False
    conn.close()

    print(f"   Found auction: {auction_info['auction_address']}")
    print(f"   Available tokens: {auction_info['initial_available']}")
    print(f"   Version: {auction_info['version']}")

    # Load the auction contract
    if auction_info['version'] == '0.0.1':
        auction = LegacyAuction.at(auction_info['auction_address'])
        print("   Using LegacyAuction contract")
    else:
        auction = Auction.at(auction_info['auction_address'])
        print("   Using modern Auction contract")

    # Load token contracts
    from_token = MockERC20Enhanced.at(auction_info['from_token'])
    want_token = MockERC20Enhanced.at(auction_info['want_token'])

    try:
        # Check available on-chain
        available = auction.available(from_token.address)
        print(f"   On-chain available: {available}")
        
        if available > 500000:  # Need some tokens
            take_amount = 250000  # Small amount
            payment_amount = 1000000  # Generous payment
            
            print(f"   💰 Minting payment tokens to taker...")
            want_token.mint(taker.address, payment_amount, {'from': deployer})
            
            print(f"   🔓 Approving payment...")
            want_token.approve(auction.address, 2**256-1, {'from': taker})
            
            print(f"   🎯 Executing Take for {take_amount} tokens...")
            from brownie import web3
            print(f"   📍 Current block: {web3.eth.block_number}")
            
            take_tx = auction.take(from_token.address, take_amount, {'from': taker})
            
            print(f"   ✅ Take successful!")
            print(f"   📍 Block: {take_tx.block_number}")
            print(f"   📍 TX: {take_tx.txid}")
            
            if 'Take' in take_tx.events:
                event = take_tx.events['Take'][0]
                print(f"   🎉 Take event emitted:")
                print(f"      from: {event['from']}")
                print(f"      taker: {event['taker']}")
                print(f"      amountTaken: {event['amountTaken']}")
                print(f"      amountPaid: {event['amountPaid']}")
                
                # Wait for indexer
                print(f"\n⏱️ Waiting 30 seconds for indexer...")
                time.sleep(30)
                
                # Check database
                print(f"   🔍 Checking database for Take event...")
                conn = psycopg2.connect("postgresql://postgres@localhost:5432/auction_dev")
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM takes 
                        WHERE transaction_hash = %s
                    """, (take_tx.txid,))
                    
                    result = cursor.fetchone()
                    if result['count'] > 0:
                        print(f"   ✅ Take found in database!")
                        
                        cursor.execute("""
                            SELECT * FROM takes 
                            WHERE transaction_hash = %s
                        """, (take_tx.txid,))
                        take = cursor.fetchone()
                        print(f"   Take details: {dict(take)}")
                        
                        cursor.execute("SELECT COUNT(*) as total FROM takes")
                        total = cursor.fetchone()
                        print(f"   Total takes in database: {total['total']}")
                        return True
                    else:
                        print(f"   ❌ Take not found in database")
                        cursor.execute("SELECT COUNT(*) as total FROM takes")
                        total = cursor.fetchone()
                        print(f"   Total takes in database: {total['total']}")
                        return False
                conn.close()
            else:
                print(f"   ❌ No Take event found in transaction")
                return False
        else:
            print(f"   ❌ Not enough tokens available: {available}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ Take transaction test completed")