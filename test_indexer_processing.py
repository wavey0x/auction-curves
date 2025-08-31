#!/usr/bin/env python3
"""
Test the indexer's _process_take function directly
"""
import sys
import os
sys.path.append('./indexer')

from indexer import AuctionIndexer
from web3 import Web3
import json

# Create indexer instance
indexer = AuctionIndexer("indexer/config.yaml")

# Get the Take event from block 66
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Load ABI
with open('build/contracts/LegacyAuction.json', 'r') as f:
    legacy_abi = json.load(f)['abi']

# Get the contract and event
auction_address = '0xB7A5bd0345EF1Cc5E66bf61BdeC17D2461fBd968'
auction_contract = w3.eth.contract(address=auction_address, abi=legacy_abi)

# Get the Take event from block 66
try:
    take_filter = auction_contract.events.Take.create_filter(
        fromBlock=66,
        toBlock=66
    )
    events = take_filter.get_all_entries()
    
    if events:
        event = events[0]
        print(f"🔍 Testing indexer processing of Take event...")
        print(f"   Event args: {dict(event.args)}")
        print(f"   Block: {event.blockNumber}")
        print(f"   Transaction: {event.transactionHash.hex()}")
        
        # Try to process this event using the indexer's method
        try:
            indexer._process_take(event, 31337, auction_address)
            print("✅ Event processed successfully!")
            
            # Check if it was inserted
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect("postgresql://postgres@localhost:5432/auction_dev")
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM takes 
                    WHERE auction_address = %s AND transaction_hash = %s
                """, (auction_address, event.transactionHash.hex()))
                
                result = cursor.fetchone()
                if result:
                    print(f"✅ Take found in database: {dict(result)}")
                else:
                    print("❌ Take not found in database")
            conn.close()
            
        except Exception as process_error:
            print(f"❌ Processing error: {process_error}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No Take events found")

except Exception as e:
    print(f"❌ Error getting events: {e}")

print("\n✅ Indexer processing test completed")