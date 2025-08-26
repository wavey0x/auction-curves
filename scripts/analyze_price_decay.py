#!/usr/bin/env python3

from brownie import accounts, MinuteStepAuction, MediumStepAuction, SmallStepAuction, MockERC20, Wei
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
    """Calculate and compare price decay for all three auction types"""
    
    deployer = accounts[0]
    receiver = accounts[1]
    
    print(f"Deploying contracts with account: {deployer}")
    
    # Deploy mock tokens
    print("Deploying mock tokens...")
    want_token = deploy_mock_token()  # Token we want to receive
    from_token = deploy_mock_token()  # Token being auctioned
    
    # Deploy auction contracts
    print("Deploying auction contracts...")
    minute_step_auction = MinuteStepAuction.deploy({'from': deployer})
    medium_step_auction = MediumStepAuction.deploy({'from': deployer})
    small_step_auction = SmallStepAuction.deploy({'from': deployer})
    
    # Initialize auctions with different parameters
    starting_price = 1_000_000 * 10**18  # 1M tokens (1M * 1e18)
    standard_length = 24 * 3600  # 24 hours in seconds
    extended_length = 36 * 3600  # 36 hours in seconds
    
    print("Initializing auctions...")
    minute_step_auction.initialize(
        want_token.address,
        receiver.address, 
        deployer.address,
        standard_length,
        starting_price,
        {'from': deployer}
    )
    
    medium_step_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        standard_length,
        starting_price,
        {'from': deployer}
    )
    
    small_step_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        extended_length,  # 36 hours for small step
        starting_price,
        {'from': deployer}
    )
    
    # Enable auctions for the from_token
    print("Enabling auctions...")
    minute_step_auction.enable(from_token.address, {'from': deployer})
    medium_step_auction.enable(from_token.address, {'from': deployer})
    small_step_auction.enable(from_token.address, {'from': deployer})
    
    # Transfer tokens to auction contracts
    token_amount = 1 * 10**18  # 1e18 tokens
    from_token.mint(minute_step_auction.address, token_amount, {'from': deployer})
    from_token.mint(medium_step_auction.address, token_amount, {'from': deployer})
    from_token.mint(small_step_auction.address, token_amount, {'from': deployer})
    
    # Kick off auctions
    print("Kicking off auctions...")
    minute_step_auction.kick(from_token.address, {'from': deployer})
    medium_step_auction.kick(from_token.address, {'from': deployer})
    small_step_auction.kick(from_token.address, {'from': deployer})
    
    # Get kicked timestamps
    minute_kicked = minute_step_auction.kicked(from_token.address)
    medium_kicked = medium_step_auction.kicked(from_token.address)
    small_kicked = small_step_auction.kicked(from_token.address)
    
    print(f"Minute-step auction kicked at: {minute_kicked}")
    print(f"Medium-step auction kicked at: {medium_kicked}")
    print(f"Small-step auction kicked at: {small_kicked}")
    
    # Calculate prices over 36 hours
    hours = np.linspace(0, 36, 36*60)  # Every minute for 36 hours
    minute_step_prices = []
    medium_step_prices = []
    small_step_prices = []
    
    print("Calculating price curves...")
    for hour in hours:
        minute_timestamp = int(minute_kicked + hour * 3600)
        medium_timestamp = int(medium_kicked + hour * 3600)
        small_timestamp = int(small_kicked + hour * 3600)
        
        # Get prices for 1e18 tokens
        try:
            minute_price = minute_step_auction.price(from_token.address, minute_timestamp) / 1e18
            medium_price = medium_step_auction.price(from_token.address, medium_timestamp) / 1e18
            small_price = small_step_auction.price(from_token.address, small_timestamp) / 1e18
        except:
            # Price might be 0 after auction ends
            minute_price = 0
            medium_price = 0 
            small_price = 0
            
        minute_step_prices.append(minute_price)
        medium_step_prices.append(medium_price)
        small_step_prices.append(small_price)
    
    # Calculate step sizes (percentage price change per update)
    minute_step_change = (1 - 0.988514020352896135356867505) * 100  # % change per minute
    medium_step_change = (1 - 0.993092495437035901533210216) * 100  # % change per 36s
    small_step_change = (1 - 0.995389679103229139420708864) * 100   # % change per 36s
    
    # Create the plot
    plt.figure(figsize=(14, 8))
    plt.plot(hours, minute_step_prices, 
             label=f'Minute-Step (60s steps, -{minute_step_change:.2f}%/step, 24h)', 
             linewidth=2, color='blue')
    plt.plot(hours, medium_step_prices, 
             label=f'Medium-Step (36s steps, -{medium_step_change:.2f}%/step, 24h)', 
             linewidth=2, color='red')
    plt.plot(hours, small_step_prices, 
             label=f'Small-Step (36s steps, -{small_step_change:.2f}%/step, 36h)', 
             linewidth=2, color='green')
    
    plt.xlabel('Hours since auction start')
    plt.ylabel('Price per 1e18 tokens')
    plt.title('Dutch Auction Price Decay Comparison - Three Step Intervals')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add vertical lines to show auction end times
    plt.axvline(x=24, color='gray', linestyle='--', alpha=0.5, label='24h mark')
    plt.axvline(x=36, color='gray', linestyle='--', alpha=0.5, label='36h mark')
    
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