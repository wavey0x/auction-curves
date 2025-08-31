#!/usr/bin/env python3
"""
Proper test of take functionality with correct token setup
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

    print("🧪 Testing take with proper token setup...")

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

    # Get from token (being auctioned)
    from_token_info = deployment_data['tokens'][auction_info['from_token']]
    from_token = MockERC20Enhanced.at(from_token_info['address'])

    # Get to token (payment token)
    to_token_info = deployment_data['tokens'][auction_info['to_token']]
    to_token = MockERC20Enhanced.at(to_token_info['address'])

    print(f"   From token: {from_token_info['symbol']} at {from_token.address}")
    print(f"   To token: {to_token_info['symbol']} at {to_token.address}")

    try:
        # Check auction state
        available = auction.available(from_token.address)
        print(f"   Available amount: {available}")
        
        if available > 0:
            # Calculate take amount (5% of available to be safe)
            take_amount = available // 20
            print(f"   Taking {take_amount} tokens (5% of available)")
            
            # STEP 1: Mint a large amount of payment tokens to taker
            # Use a generous amount for payment
            payment_amount = take_amount * 10  # 10x for safety
            print(f"   💰 Minting {payment_amount} {to_token_info['symbol']} to taker...")
            mint_tx = to_token.mint(taker.address, payment_amount, {'from': deployer})
            print(f"      ✅ Minted (tx: {mint_tx.txid[:10]}...)")
            
            # Verify mint worked
            taker_balance = to_token.balanceOf(taker.address)
            print(f"      Taker {to_token_info['symbol']} balance: {taker_balance}")
            
            # STEP 2: Give unlimited approval for payment tokens
            print(f"   🔓 Approving unlimited {to_token_info['symbol']} spending...")
            max_approval = 2**256 - 1  # Max uint256
            approve_tx = to_token.approve(auction.address, max_approval, {'from': taker})
            print(f"      ✅ Approved (tx: {approve_tx.txid[:10]}...)")
            
            # Verify approval
            allowance = to_token.allowance(taker.address, auction.address)
            print(f"      Allowance: {allowance}")
            
            # STEP 3: Execute the take
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
                return True
            else:
                print(f"   ⚠️ No Take event found in transaction")
                print(f"   Events found: {list(take_tx.events.keys())}")
                return False
        else:
            print("   ❌ No tokens available")
            return False
            
    except Exception as e:
        print(f"   ❌ Take failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ Take test completed")