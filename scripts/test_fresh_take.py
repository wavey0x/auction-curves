#!/usr/bin/env python3
"""
Create a fresh Take transaction and monitor indexing
"""
from brownie import accounts, LegacyAuction, MockERC20Enhanced
import json
import time

def main():
    # Load deployment info  
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)

    # Use accounts
    deployer = accounts[0]
    taker = accounts[2]  # Different taker

    print("🎯 Creating fresh Take transaction for real-time monitoring...")

    # Use first auction
    auction_info = deployment_data['auctions'][0]
    auction = LegacyAuction.at(auction_info['address'])
    from_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['from_token']]['address'])
    to_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['to_token']]['address'])

    print(f"   Auction: {auction_info['from_token']}→{auction_info['to_token']}")
    print(f"   Address: {auction.address}")

    try:
        # Check available
        available = auction.available(from_token.address)
        print(f"   Available: {available}")
        
        if available > 1000000:  # Need some tokens
            take_amount = 500000  # Small amount
            payment_amount = 2000000  # Generous payment
            
            print(f"   💰 Minting payment tokens to new taker...")
            to_token.mint(taker.address, payment_amount, {'from': deployer})
            
            print(f"   🔓 Approving payment...")
            to_token.approve(auction.address, 2**256-1, {'from': taker})
            
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
                print(f"      amountTaken: {event['amountTaken']}")
                print(f"      amountPaid: {event['amountPaid']}")
                
                # Now wait and check if indexer picks it up
                print(f"\n⏱️ Waiting 30 seconds for indexer...")
                time.sleep(30)
                
                print(f"   🔍 Checking database...")
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
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
                        return True
                    else:
                        print(f"   ❌ Take not found in database")
                        
                        # Check total takes count
                        cursor.execute("SELECT COUNT(*) as total FROM takes")
                        total = cursor.fetchone()
                        print(f"   Total takes in database: {total['total']}")
                        return False
                conn.close()
            else:
                print(f"   ❌ No Take event found")
                return False
        else:
            print(f"   ❌ Not enough tokens available")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ Fresh take test completed")