#!/usr/bin/env python3
"""
Manual test of take functionality with the new Take events
"""
from brownie import accounts, Auction, LegacyAuction, MockERC20Enhanced
import json

def main():
    # Load deployment info  
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)

    # Use accounts
    deployer = accounts[0]
    taker = accounts[1]

    print("🧪 Testing manual take transactions with new Take events...")

    # Test the first auction
    auction_info = deployment_data['auctions'][0]
print(f"\n📊 Testing auction {auction_info['from_token']}→{auction_info['to_token']}")
print(f"   Address: {auction_info['address']}")
print(f"   Type: {auction_info['type']}")

# Get auction contract
if auction_info['type'] == 'legacy':
    auction = LegacyAuction.at(auction_info['address'])
else:
    auction = Auction.at(auction_info['address'])

# Get from token
from_token_info = deployment_data['tokens'][auction_info['from_token']]
from_token = MockERC20Enhanced.at(from_token_info['address'])

# Get to token (want token)
to_token_info = deployment_data['tokens'][auction_info['to_token']]
to_token = MockERC20Enhanced.at(to_token_info['address'])

print(f"   From token: {from_token_info['symbol']} at {from_token.address}")
print(f"   To token: {to_token_info['symbol']} at {to_token.address}")

try:
    # Check auction state
    available = auction.available(from_token.address)
    print(f"   Available amount: {available}")
    
    if available == 0:
        print("   ⚠️ No tokens available - auction may not be kicked")
        # Try to kick it
        print("   🚀 Attempting to kick auction...")
        kick_tx = auction.kick(from_token.address, {'from': deployer})
        print(f"   ✅ Kicked auction (tx: {kick_tx.txid[:10]}...)")
        
        # Check again
        available = auction.available(from_token.address)
        print(f"   New available amount: {available}")
    
    if available > 0:
        # Calculate take amount (10% of available)
        take_amount = available // 10
        print(f"   Taking {take_amount} tokens (10% of available)")
        
        # Mint payment tokens to taker
        payment_estimate = take_amount * 2  # Generous estimate
        to_token.mint(taker.address, payment_estimate, {'from': deployer})
        print(f"   Minted {payment_estimate} {to_token_info['symbol']} to taker")
        
        # Approve auction to spend payment tokens
        to_token.approve(auction.address, payment_estimate, {'from': taker})
        print(f"   Approved auction to spend payment tokens")
        
        # Execute the take
        print(f"   🎯 Executing take transaction...")
        take_tx = auction.take(from_token.address, take_amount, {'from': taker})
        print(f"   ✅ Take successful! (tx: {take_tx.txid[:10]}...)")
        
        # Check for Take events
        if 'Take' in take_tx.events:
            take_event = take_tx.events['Take'][0]
            print(f"   🎉 Take event emitted!")
            print(f"      from: {take_event['from']}")
            print(f"      taker: {take_event['taker']}")
            print(f"      amountTaken: {take_event['amountTaken']}")
            print(f"      amountPaid: {take_event['amountPaid']}")
        else:
            print(f"   ⚠️ No Take event found in transaction")
            print(f"   Events found: {list(take_tx.events.keys())}")
    else:
        print("   ❌ Still no tokens available after kick")
        
except Exception as e:
    print(f"   ❌ Take failed: {e}")

print("\n✅ Manual take test completed")