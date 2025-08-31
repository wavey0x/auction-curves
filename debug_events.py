#!/usr/bin/env python3
"""
Debug script to check what events were emitted on the blockchain
"""
from web3 import Web3
import json

# Connect to Anvil
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Load deployment info
with open('deployment_info.json', 'r') as f:
    deployment_data = json.load(f)

# Check latest block
latest_block = w3.eth.block_number
print(f"Latest block: {latest_block}")

# Load auction ABI
with open('build/contracts/Auction.json', 'r') as f:
    auction_abi = json.load(f)['abi']

# Load legacy auction ABI  
with open('build/contracts/LegacyAuction.json', 'r') as f:
    legacy_auction_abi = json.load(f)['abi']

# Check first few auctions for events
for auction in deployment_data['auctions'][:3]:
    print(f"\n=== Checking auction {auction['from_token']}→{auction['to_token']} ===")
    print(f"Address: {auction['address']}")
    print(f"Type: {auction['type']}")
    
    # Get the appropriate ABI
    abi = legacy_auction_abi if auction['type'] == 'legacy' else auction_abi
    
    # Create contract instance
    contract = w3.eth.contract(address=auction['address'], abi=abi)
    
    # Check for AuctionKicked events
    try:
        kick_filter = contract.events.AuctionKicked.create_filter(fromBlock=0, toBlock='latest')
        kick_events = kick_filter.get_all_entries()
        print(f"AuctionKicked events: {len(kick_events)}")
        for event in kick_events:
            print(f"  Block {event.blockNumber}: {event.event}")
    except Exception as e:
        print(f"  No AuctionKicked events or error: {e}")
    
    # Check for Take events
    try:
        take_filter = contract.events.Take.create_filter(fromBlock=0, toBlock='latest') 
        take_events = take_filter.get_all_entries()
        print(f"Take events: {len(take_events)}")
        for event in take_events:
            print(f"  Block {event.blockNumber}: {event.event} - {dict(event.args)}")
    except Exception as e:
        print(f"  No Take events or error: {e}")
        
    # Check for AuctionTake events (legacy)
    try:
        take_filter = contract.events.AuctionTake.create_filter(fromBlock=0, toBlock='latest')
        take_events = take_filter.get_all_entries()
        print(f"AuctionTake events: {len(take_events)}")
        for event in take_events:
            print(f"  Block {event.blockNumber}: {event.event} - {dict(event.args)}")
    except Exception as e:
        print(f"  No AuctionTake events or error: {e}")

print(f"\nTotal blocks scanned: 0 to {latest_block}")