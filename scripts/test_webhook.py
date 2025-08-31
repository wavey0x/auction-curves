from brownie import Auction, LegacyAuction, accounts
import time

def main():
    print("🧪 Testing Rindexer webhook functionality...")
    
    # Test both modern and legacy auction events
    modern_auction = Auction.at('0x9f9D6AF359b4540C7b50ec0D7d6D52c8A3f5f2FA')
    legacy_auction = LegacyAuction.at('0x9E02f3a8567587D27d7EB1D087408D062b4c6a1c')
    
    print(f"📍 Modern auction: {modern_auction.address}")
    print(f"📍 Legacy auction: {legacy_auction.address}")
    
    # Kick modern auction to generate AuctionKicked event
    print("🚀 Kicking modern auction...")
    try:
        tx1 = modern_auction.kick({'from': accounts[0]})
        print(f"✅ Modern kick success - Block: {tx1.block_number}, Hash: {tx1.txid}")
    except Exception as e:
        print(f"❌ Modern kick failed: {e}")
    
    time.sleep(2)
    
    # Kick legacy auction to generate AuctionKicked event  
    print("🚀 Kicking legacy auction...")
    try:
        tx2 = legacy_auction.kick({'from': accounts[0]})
        print(f"✅ Legacy kick success - Block: {tx2.block_number}, Hash: {tx2.txid}")
    except Exception as e:
        print(f"❌ Legacy kick failed: {e}")
    
    print("🎯 Webhook test events generated!")
    print("   Check http://localhost:8000/webhook/process-event logs")
    print("   Check public.auctions table for new records")
