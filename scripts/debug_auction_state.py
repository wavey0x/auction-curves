#!/usr/bin/env python3
"""
Debug auction state to understand why takes are failing
"""
from brownie import accounts, LegacyAuction, Auction, MockERC20Enhanced, web3
import json

def main():
    # Load deployment info  
    with open('deployment_info.json', 'r') as f:
        deployment_data = json.load(f)

    print("🔍 Debugging auction state...")

    # Check a few auctions
    for i, auction_info in enumerate(deployment_data['auctions'][:3]):
        print(f"\n📊 Auction {i+1}: {auction_info['from_token']}→{auction_info['to_token']}")
        print(f"   Address: {auction_info['address']}")
        
        try:
            if auction_info.get('type') == 'legacy':
                auction = LegacyAuction.at(auction_info['address'])
                print("   Type: Legacy")
            else:
                auction = Auction.at(auction_info['address'])
                print("   Type: Modern")
            
            from_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['from_token']]['address'])
            to_token = MockERC20Enhanced.at(deployment_data['tokens'][auction_info['to_token']]['address'])
            
            print(f"   From Token: {from_token.symbol()} ({from_token.address})")
            print(f"   To Token: {to_token.symbol()} ({to_token.address})")
            
            # Check key auction parameters
            try:
                available = auction.available(from_token.address)
                print(f"   ✅ Available: {available}")
            except Exception as e:
                print(f"   ❌ Available check failed: {e}")
                continue
            
            if available > 0:
                print(f"   🎯 This auction has tokens! Testing further...")
                
                try:
                    # Check if auction is enabled
                    enabled = auction.enabled(from_token.address)
                    print(f"   Enabled: {enabled}")
                except:
                    print(f"   Enabled: Cannot check")
                
                try:
                    # Check current price  
                    price = auction.price(from_token.address)
                    print(f"   Current Price: {price}")
                except Exception as e:
                    print(f"   Price check failed: {e}")
                
                try:
                    # Check token balances
                    auction_from_balance = from_token.balanceOf(auction.address)
                    auction_to_balance = to_token.balanceOf(auction.address)
                    print(f"   Auction from_token balance: {auction_from_balance}")
                    print(f"   Auction to_token balance: {auction_to_balance}")
                except Exception as e:
                    print(f"   Balance check failed: {e}")
                
                # Let's try a very small take
                try:
                    print(f"   🧪 Testing take simulation...")
                    taker = accounts[1]
                    
                    # Mint some payment tokens
                    to_token.mint(taker.address, 10**24, {'from': accounts[0]})
                    to_token.approve(auction.address, 2**256-1, {'from': taker})
                    
                    # Minimal take amount
                    take_amount = min(100000, available // 100)  # Very small amount
                    print(f"   Testing take amount: {take_amount}")
                    
                    # Call take (this will show the revert reason)
                    auction.take(from_token.address, take_amount, {'from': taker})
                    
                except Exception as e:
                    print(f"   ❌ Take simulation failed: {e}")
                
                break  # Stop after first working auction
            else:
                print(f"   ⏭️ Skipping - no tokens available")
                
        except Exception as e:
            print(f"   ❌ Failed to check auction: {e}")

if __name__ == "__main__":
    main()
