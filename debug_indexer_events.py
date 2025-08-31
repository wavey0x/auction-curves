#!/usr/bin/env python3
"""
Debug the indexer's event processing for the Take event
"""
from web3 import Web3
import json

# Connect to Anvil
w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

# Load auction ABIs
with open('build/contracts/LegacyAuction.json', 'r') as f:
    legacy_abi = json.load(f)['abi']

# Check block 66 which had our successful Take
block_number = 66
block = w3.eth.get_block(block_number, full_transactions=True)

print(f"🔍 Analyzing block {block_number}...")
print(f"   Block hash: {block['hash'].hex()}")
print(f"   Timestamp: {block['timestamp']}")
print(f"   Transactions: {len(block['transactions'])}")

# Find the Take transaction
take_tx_hash = '0xa1a71885a103e46b228f475e3165f9a31c4f9065bafe58b748e59487a7b8ea3c'

for tx in block['transactions']:
    if tx['hash'].hex() == take_tx_hash:
        print(f"\n✅ Found Take transaction:")
        print(f"   To: {tx['to']}")
        print(f"   Gas used: {w3.eth.get_transaction_receipt(tx['hash'])['gasUsed']}")
        
        # Get transaction receipt and check logs
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        print(f"   Status: {receipt['status']}")
        print(f"   Logs: {len(receipt['logs'])}")
        
        # Check for Take events
        auction_address = tx['to']
        auction_contract = w3.eth.contract(address=auction_address, abi=legacy_abi)
        
        # Get Take events from this transaction
        take_events = auction_contract.events.Take().process_receipt(receipt)
        print(f"   Take events found: {len(take_events)}")
        
        for i, event in enumerate(take_events):
            print(f"   Take event #{i}:")
            print(f"      from: {event['args']['from']}")
            print(f"      taker: {event['args']['taker']}")
            print(f"      amountTaken: {event['args']['amountTaken']}")
            print(f"      amountPaid: {event['args']['amountPaid']}")
            print(f"      block: {event['blockNumber']}")
            print(f"      logIndex: {event['logIndex']}")
        
        break
else:
    print(f"❌ Take transaction not found in block {block_number}")

print("\n🔍 Checking if indexer can see this event...")

# Simulate what the indexer does - create event filter for this block range
auction_address = '0xB7A5bd0345EF1Cc5E66bf61BdeC17D2461fBd968'
auction_contract = w3.eth.contract(address=auction_address, abi=legacy_abi)

try:
    take_filter = auction_contract.events.Take.create_filter(
        fromBlock=block_number,
        toBlock=block_number
    )
    events = take_filter.get_all_entries()
    print(f"✅ Filter found {len(events)} Take events in block {block_number}")
    
    for event in events:
        print(f"   Event: {dict(event.args)}")
        
except Exception as e:
    print(f"❌ Filter error: {e}")

print("\n✅ Event analysis completed")