#!/usr/bin/env python3

from brownie import accounts, Auction, ModifiedAuction, MockERC20, Wei
import matplotlib.pyplot as plt
import numpy as np
import time

# Deploy a mock ERC20 token for testing
def deploy_mock_token():
    """Deploy a simple mock ERC20 token for testing"""
    deployer = accounts[0]
    mock_token = MockERC20.deploy({'from': deployer})
    return mock_token

def calculate_price_over_time():
    """Calculate and compare price decay for both auction types over 24 hours"""
    
    deployer = accounts[0]
    receiver = accounts[1]
    
    print(f"Deploying contracts with account: {deployer}")
    
    # Deploy mock tokens
    print("Deploying mock tokens...")
    want_token = deploy_mock_token()  # Token we want to receive
    from_token = deploy_mock_token()  # Token being auctioned
    
    # Deploy auction contracts
    print("Deploying auction contracts...")
    original_auction = Auction.deploy({'from': deployer})
    modified_auction = ModifiedAuction.deploy({'from': deployer})
    
    # Initialize both auctions with same parameters
    starting_price = 1_000_000 * 10**18  # 1M tokens (1M * 1e18)
    auction_length = 24 * 3600  # 24 hours in seconds
    
    print("Initializing auctions...")
    original_auction.initialize(
        want_token.address,
        receiver.address, 
        deployer.address,
        auction_length,
        starting_price,
        {'from': deployer}
    )
    
    modified_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        auction_length,
        starting_price,
        {'from': deployer}
    )
    
    # Enable auctions for the from_token
    print("Enabling auctions...")
    original_auction.enable(from_token.address, {'from': deployer})
    modified_auction.enable(from_token.address, {'from': deployer})
    
    # Transfer tokens to auction contracts
    token_amount = 1 * 10**18  # 1e18 tokens
    from_token.mint(original_auction.address, token_amount, {'from': deployer})
    from_token.mint(modified_auction.address, token_amount, {'from': deployer})
    
    # Kick off auctions
    print("Kicking off auctions...")
    original_auction.kick(from_token.address, {'from': deployer})
    modified_auction.kick(from_token.address, {'from': deployer})
    
    # Get kicked timestamps
    original_kicked = original_auction.kicked(from_token.address)
    modified_kicked = modified_auction.kicked(from_token.address)
    
    print(f"Original auction kicked at: {original_kicked}")
    print(f"Modified auction kicked at: {modified_kicked}")
    
    # Calculate prices over 24 hours
    hours = np.linspace(0, 24, 24*60)  # Every minute for 24 hours
    original_prices = []
    modified_prices = []
    
    print("Calculating price curves...")
    for hour in hours:
        timestamp = int(original_kicked + hour * 3600)
        
        # Get prices for 1e18 tokens
        try:
            original_price = original_auction.price(from_token.address, timestamp) / 1e18
            modified_price = modified_auction.price(from_token.address, timestamp) / 1e18
        except:
            # Price might be 0 after auction ends
            original_price = 0
            modified_price = 0
            
        original_prices.append(original_price)
        modified_prices.append(modified_price)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(hours, original_prices, label='Original Auction (60-second steps)', linewidth=2)
    plt.plot(hours, modified_prices, label='Modified Auction (36-second steps)', linewidth=2)
    
    plt.xlabel('Hours since auction start')
    plt.ylabel('Price per 1e18 tokens')
    plt.title('Dutch Auction Price Decay Comparison (24 Hours)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add some styling
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('price_decay_comparison.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'price_decay_comparison.png'")
    
    # Show the plot
    plt.show()
    
    # Print some statistics
    print(f"\nPrice Statistics:")
    print(f"Original auction starting price: {original_prices[0]:.2e}")
    print(f"Modified auction starting price: {modified_prices[0]:.2e}")
    print(f"Original auction price at 12h: {original_prices[len(hours)//2]:.2e}")
    print(f"Modified auction price at 12h: {modified_prices[len(hours)//2]:.2e}")
    print(f"Original auction final price: {original_prices[-1]:.2e}")  
    print(f"Modified auction final price: {modified_prices[-1]:.2e}")
    
    return original_prices, modified_prices, hours

def main():
    """Main function to run the analysis"""
    try:
        calculate_price_over_time()
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        print("This might be due to missing dependencies or network issues.")
        print("Make sure you have matplotlib installed: pip install matplotlib")

if __name__ == "__main__":
    main()