#!/usr/bin/env python3
"""
Script to deploy individual AuctionHouses using the factory.
"""

from brownie import accounts, AuctionFactory, Auction, MockERC20

def main():
    """Deploy a single Auction for testing"""
    deployer = accounts[0] 
    receiver = accounts[1]
    
    print("Deploying Auction components...")
    
    # Deploy factory
    factory = AuctionFactory.deploy({'from': deployer})
    print(f"Auction Factory deployed: {factory.address}")
    
    # Deploy mock tokens
    want_token = MockERC20.deploy({'from': deployer})
    from_token = MockERC20.deploy({'from': deployer})
    print(f"Want token: {want_token.address}")
    print(f"From token: {from_token.address}")
    
    # Create Auction using factory
    tx = factory.createNewAuction(
        want_token.address,
        receiver.address,
        {'from': deployer}
    )
    
    auction_address = tx.return_value
    print(f"Auction deployed: {auction_address}")
    
    # Get Auction contract instance
    auction = Auction.at(auction_address)
    
    # Enable the from token in the AuctionHouse
    auction.enableToken(from_token.address, {'from': deployer})
    print(f"Enabled {from_token.address} in AuctionHouse")
    
    # Mint some tokens to the AuctionHouse contract for testing
    from_token.mint(auction.address, 1000 * 10**18, {'from': deployer})
    print("Minted 1000 tokens to AuctionHouse contract")
    
    print("\n✅ Deployment complete!")
    print(f"Auction Factory: {factory.address}")
    print(f"Auction: {auction.address}")
    print(f"Want Token: {want_token.address}")
    print(f"From Token: {from_token.address}")

if __name__ == "__main__":
    main()