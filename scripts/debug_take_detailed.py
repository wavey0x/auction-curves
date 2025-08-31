#!/usr/bin/env python3
"""
Detailed debugging of take transaction to find exact failure point
"""
from brownie import accounts, Auction, LegacyAuction, MockERC20Enhanced, web3
import json

def main():
    # Load deployment info  
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)

    # Use accounts
    deployer = accounts[0]
    taker = accounts[1]

    print("🔍 Detailed take debugging...")

    # Test the first auction
    auction_info = deployment_data['auctions'][0]
    print(f"\n📊 Testing auction {auction_info['from_token']}→{auction_info['to_token']}")

    # Get contracts
    if auction_info['type'] == 'legacy':
        auction = LegacyAuction.at(auction_info['address'])
    else:
        auction = Auction.at(auction_info['address'])

    from_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['from_token']]['address'])
    to_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['to_token']]['address'])

    print(f"   From token: {from_token.symbol()} (decimals: {from_token.decimals()})")
    print(f"   To token: {to_token.symbol()} (decimals: {to_token.decimals()})")

    try:
        # Get detailed auction state
        auction_data = auction.auctions(from_token.address)
        kicked_time = auction_data[0]
        scaler = auction_data[1]
        initial_available = auction_data[2]
        
        # Get wantInfo
        want_address = auction.want()
        print(f"   Want address: {want_address}")
        
        # Get current state
        available = auction.available(from_token.address)
        current_block = web3.eth.get_block('latest')
        current_time = current_block['timestamp']
        
        print(f"\n📊 Auction Details:")
        print(f"   Kicked time: {kicked_time}")
        print(f"   Current time: {current_time}")
        print(f"   Time elapsed: {current_time - kicked_time}")
        print(f"   Scaler: {scaler}")
        print(f"   Initial available: {initial_available}")
        print(f"   Available now: {available}")
        
        # Try a very small take amount
        take_amount = 1000000  # 1M units (small amount)
        print(f"\n🎯 Testing take of {take_amount} tokens...")
        
        # Setup tokens
        payment_amount = take_amount * 1000  # Way more than needed
        print(f"   💰 Minting {payment_amount} payment tokens...")
        to_token.mint(taker.address, payment_amount, {'from': deployer})
        
        print(f"   🔓 Approving unlimited spending...")
        max_approval = 2**256 - 1
        to_token.approve(auction.address, max_approval, {'from': taker})
        
        # Check balances before
        taker_from_before = from_token.balanceOf(taker.address)
        taker_to_before = to_token.balanceOf(taker.address)
        auction_from_before = from_token.balanceOf(auction.address)
        
        print(f"\n💰 Balances Before:")
        print(f"   Taker {from_token.symbol()}: {taker_from_before}")
        print(f"   Taker {to_token.symbol()}: {taker_to_before}")
        print(f"   Auction {from_token.symbol()}: {auction_from_before}")
        
        # Try the take with better error handling
        print(f"\n🎯 Executing take...")
        try:
            # Use call first to see what would happen
            try:
                auction.take.call(from_token.address, take_amount, {'from': taker})
                print("   ✅ Call simulation successful")
            except Exception as call_error:
                print(f"   ❌ Call simulation failed: {call_error}")
                
                # Try to get the actual revert reason
                try:
                    auction.take(from_token.address, take_amount, {'from': taker, 'allow_revert': True})
                except Exception as revert_error:
                    print(f"   Detailed revert: {revert_error}")
                return
            
            # If call worked, do the actual transaction  
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
                print(f"   ⚠️ No Take event found")
                print(f"   Events: {list(take_tx.events.keys())}")
                
        except Exception as take_error:
            print(f"   ❌ Take transaction failed: {take_error}")
            return False
            
    except Exception as e:
        print(f"   ❌ Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ Detailed debugging completed")