#!/usr/bin/env python3

from brownie import accounts, ParameterizedAuction, MockERC20, Wei
import matplotlib.pyplot as plt
import numpy as np
import time
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Deploy a mock ERC20 token for testing
def deploy_mock_token():
    """Deploy a simple mock ERC20 token for testing"""
    deployer = accounts[0]
    mock_token = MockERC20.deploy({'from': deployer})
    return mock_token

def calculate_price_over_time():
    """Calculate and compare price decay using ParameterizedAuction with different decay factors"""
    
    deployer = accounts[0]
    receiver = accounts[1]
    
    print(f"Deploying contracts with account: {deployer}")
    
    # Deploy mock tokens
    print("Deploying mock tokens...")
    want_token = deploy_mock_token()  # Token we want to receive
    from_token = deploy_mock_token()  # Token being auctioned
    
    # Deploy ParameterizedAuction contracts with different parameters
    print("Deploying parameterized auction contracts...")
    
    # Auction 1: Custom test decay (configurable) - moved to first position
    custom_auction = ParameterizedAuction.deploy(
        60,                                    # 60 seconds interval
        0.988514020352896135_356867505 * 10 ** 27,
        0,                                     # dynamic pricing
        {'from': deployer}
    )
    
    # Auction 2: Half-Life Decay (1-hour half-life, 36s steps)
    half_life_auction = ParameterizedAuction.deploy(
        36,                                    # 36 seconds interval
        0.9925 * 10 ** 27,
        0,                                     # dynamic pricing
        {'from': deployer}
    )
    
    # Auction 3: Extended Decay (36h duration, same final price as 24h)
    extended_auction = ParameterizedAuction.deploy(
        36,                                    # 36 seconds interval  
        0.995 * 10 ** 27,
        0,                                     # dynamic pricing
        {'from': deployer}
    )
    
    # Auction 4: Fixed 0.2% Decay with 2400 starting price (36s intervals)
    fixed_auction = ParameterizedAuction.deploy(
        36,                                    # 36 seconds interval
        0.997 * 10 ** 27,
        0,                   
        {'from': deployer}
    )
    
    # Auction 5: Fixed 0.2% Decay with 2400 starting price (24s intervals)  
    fixed_24s_auction = ParameterizedAuction.deploy(
        24,                                    # 24 seconds interval
        997_000_000_000_000_000_000_000_000,  # 0.998 in RAY (0.3% decay)
        0,                   
        {'from': deployer}
    )
    
    # Initialize auctions with different parameters
    starting_price = 1_000_000 * 10**18  # 1M tokens (1M * 1e18)
    standard_length = 24 * 3600  # 24 hours in seconds
    extended_length = 36 * 3600  # 36 hours in seconds
    
    print("Initializing auctions...")
    custom_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        standard_length,
        starting_price,
        {'from': deployer}
    )
    
    half_life_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        standard_length,
        starting_price,
        {'from': deployer}
    )
    
    extended_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        extended_length,  # 36 hours for extended auction
        starting_price,
        {'from': deployer}
    )
    
    fixed_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        standard_length,
        starting_price,  # This will be ignored - fixed at 2400
        {'from': deployer}
    )
    
    fixed_24s_auction.initialize(
        want_token.address,
        receiver.address,
        deployer.address, 
        standard_length,
        starting_price,  # This will be ignored - fixed at 2400
        {'from': deployer}
    )
    
    # Enable auctions for the from_token
    print("Enabling auctions...")
    custom_auction.enable(from_token.address, {'from': deployer})
    half_life_auction.enable(from_token.address, {'from': deployer})
    extended_auction.enable(from_token.address, {'from': deployer})
    fixed_auction.enable(from_token.address, {'from': deployer})
    fixed_24s_auction.enable(from_token.address, {'from': deployer})
    
    # Transfer tokens to auction contracts
    token_amount = 1 * 10**18  # 1e18 tokens
    from_token.mint(custom_auction.address, token_amount, {'from': deployer})
    from_token.mint(half_life_auction.address, token_amount, {'from': deployer})
    from_token.mint(extended_auction.address, token_amount, {'from': deployer})
    from_token.mint(fixed_auction.address, token_amount, {'from': deployer})
    from_token.mint(fixed_24s_auction.address, token_amount, {'from': deployer})
    
    # Kick off auctions
    print("Kicking off auctions...")
    custom_auction.kick(from_token.address, {'from': deployer})
    half_life_auction.kick(from_token.address, {'from': deployer})
    extended_auction.kick(from_token.address, {'from': deployer})
    fixed_auction.kick(from_token.address, {'from': deployer})
    fixed_24s_auction.kick(from_token.address, {'from': deployer})
    
    # Get kicked timestamps
    custom_kicked = custom_auction.kicked(from_token.address)
    half_life_kicked = half_life_auction.kicked(from_token.address)
    extended_kicked = extended_auction.kicked(from_token.address)
    fixed_kicked = fixed_auction.kicked(from_token.address)
    fixed_24s_kicked = fixed_24s_auction.kicked(from_token.address)
    
    print(f"Half-life auction kicked at: {half_life_kicked}")
    print(f"Extended auction kicked at: {extended_kicked}")
    print(f"Fixed auction kicked at: {fixed_kicked}")
    print(f"Fixed 24s auction kicked at: {fixed_24s_kicked}")
    print(f"Custom auction kicked at: {custom_kicked}")
    
    # Calculate prices over 36 hours
    hours = np.linspace(0, 36, 36*60)  # Every minute for 36 hours
    custom_prices = []
    half_life_prices = []
    extended_prices = []
    fixed_prices = []
    fixed_24s_prices = []
    
    print("Calculating price curves...")
    for hour in hours:
        custom_timestamp = int(custom_kicked + hour * 3600)
        half_life_timestamp = int(half_life_kicked + hour * 3600)
        extended_timestamp = int(extended_kicked + hour * 3600)
        fixed_timestamp = int(fixed_kicked + hour * 3600)
        fixed_24s_timestamp = int(fixed_24s_kicked + hour * 3600)
        
        # Get prices for 1e18 tokens
        try:
            # Check if auctions have ended (24h for most, 36h for extended)
            custom_ended = (hour >= 24)
            half_life_ended = (hour >= 24)
            extended_ended = (hour >= 36) 
            fixed_ended = (hour >= 24)
            fixed_24s_ended = (hour >= 24)
            
            custom_price = None if custom_ended else custom_auction.price(from_token.address, custom_timestamp) / 1e18
            half_life_price = None if half_life_ended else half_life_auction.price(from_token.address, half_life_timestamp) / 1e18
            extended_price = None if extended_ended else extended_auction.price(from_token.address, extended_timestamp) / 1e18
            fixed_price = None if fixed_ended else fixed_auction.price(from_token.address, fixed_timestamp) / 1e18
            fixed_24s_price = None if fixed_24s_ended else fixed_24s_auction.price(from_token.address, fixed_24s_timestamp) / 1e18
        except:
            # Handle errors
            custom_price = None
            half_life_price = None
            extended_price = None
            fixed_price = None
            fixed_24s_price = None
            
        custom_prices.append(custom_price)
        half_life_prices.append(half_life_price)
        extended_prices.append(extended_price)
        fixed_prices.append(fixed_price)
        fixed_24s_prices.append(fixed_24s_price)
    
    # Calculate step sizes (percentage price change per update)
    half_life_step_change = (1 - 0.993092495437035901533210216) * 100    # % change per 36s
    extended_step_change = (1 - 0.995389679103229139420708864) * 100     # % change per 36s
    fixed_step_change = (1 - 0.998) * 100                               # % change per 36s (0.2%)
    custom_step_change = (1 - 0.99) * 100                               # % change per 60s (1.0%)
    
    # Get decay factors from deployed contracts
    custom_decay = custom_auction.STEP_DECAY() / 1e27
    half_life_decay = half_life_auction.STEP_DECAY() / 1e27
    extended_decay = extended_auction.STEP_DECAY() / 1e27  
    fixed_decay = fixed_auction.STEP_DECAY() / 1e27
    fixed_24s_decay = fixed_24s_auction.STEP_DECAY() / 1e27
    
    # Get update intervals from deployed contracts
    custom_interval = custom_auction.PRICE_UPDATE_INTERVAL()
    half_life_interval = half_life_auction.PRICE_UPDATE_INTERVAL()
    extended_interval = extended_auction.PRICE_UPDATE_INTERVAL()
    fixed_interval = fixed_auction.PRICE_UPDATE_INTERVAL()
    fixed_24s_interval = fixed_24s_auction.PRICE_UPDATE_INTERVAL()
    
    print(f"Deployed contract parameters:")
    print(f"  Custom:    {custom_interval}s intervals, {custom_decay:.6f} decay factor")
    print(f"  Half-Life: {half_life_interval}s intervals, {half_life_decay:.6f} decay factor")
    print(f"  Extended:  {extended_interval}s intervals, {extended_decay:.6f} decay factor")
    print(f"  Fixed:     {fixed_interval}s intervals, {fixed_decay:.6f} decay factor")
    print(f"  Fixed 24s: {fixed_24s_interval}s intervals, {fixed_24s_decay:.6f} decay factor")
    
    # Create filtered arrays for plotting (exclude None values)
    def filter_data(times, prices):
        filtered_times = []
        filtered_prices = []
        for t, p in zip(times, prices):
            if p is not None:
                filtered_times.append(t)
                filtered_prices.append(p)
        return filtered_times, filtered_prices
    
    custom_hours, custom_filtered = filter_data(hours, custom_prices)
    half_life_hours, half_life_filtered = filter_data(hours, half_life_prices)
    extended_hours, extended_filtered = filter_data(hours, extended_prices)
    fixed_hours, fixed_filtered = filter_data(hours, fixed_prices)
    fixed_24s_hours, fixed_24s_filtered = filter_data(hours, fixed_24s_prices)
    
    # Calculate price ranges for chart scaling
    all_prices = []
    for prices in [custom_filtered, half_life_filtered, extended_filtered, fixed_filtered, fixed_24s_filtered]:
        all_prices.extend([p for p in prices if p is not None and p > 0])
    
    # Create the plot with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 14))
    
    # Linear scale plot (top)
    ax1.plot(custom_hours, custom_filtered, 
             label=f'Auction 1 ({custom_interval}s, -{(1-custom_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='blue')
    ax1.plot(half_life_hours, half_life_filtered, 
             label=f'Auction 2 ({half_life_interval}s, -{(1-half_life_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='red')
    ax1.plot(extended_hours, extended_filtered, 
             label=f'Auction 3 ({extended_interval}s, -{(1-extended_decay)*100:.2f}%/step, 36h)', 
             linewidth=2, color='green')
    ax1.plot(fixed_hours, fixed_filtered, 
             label=f'Auction 4 ({fixed_interval}s, -{(1-fixed_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='orange')
    ax1.plot(fixed_24s_hours, fixed_24s_filtered, 
             label=f'Auction 5 ({fixed_24s_interval}s, -{(1-fixed_24s_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='purple')
    
    ax1.set_xlabel('Hours since auction start')
    ax1.set_ylabel('Price per 1e18 tokens')
    ax1.set_title('Dutch Auction Price Decay Comparison - Linear Scale')
    
    # Set y-axis limits to show full range starting from 0
    if all_prices:
        max_price = max(all_prices)
        ax1.set_ylim(0, max_price * 1.1)  # Start from 0, add 10% margin at top
    
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add vertical lines to show auction end times
    ax1.axvline(x=24, color='gray', linestyle='--', alpha=0.5)
    ax1.axvline(x=36, color='gray', linestyle='--', alpha=0.5)
    
    # Log scale plot (bottom)
    ax2.plot(custom_hours, custom_filtered, 
             label=f'Auction 1 ({custom_interval}s, -{(1-custom_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='blue')
    ax2.plot(half_life_hours, half_life_filtered, 
             label=f'Auction 2 ({half_life_interval}s, -{(1-half_life_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='red')
    ax2.plot(extended_hours, extended_filtered, 
             label=f'Auction 3 ({extended_interval}s, -{(1-extended_decay)*100:.2f}%/step, 36h)', 
             linewidth=2, color='green')
    ax2.plot(fixed_hours, fixed_filtered, 
             label=f'Auction 4 ({fixed_interval}s, -{(1-fixed_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='orange')
    ax2.plot(fixed_24s_hours, fixed_24s_filtered, 
             label=f'Auction 5 ({fixed_24s_interval}s, -{(1-fixed_24s_decay)*100:.2f}%/step, 24h)', 
             linewidth=2, color='purple')
    
    ax2.set_xlabel('Hours since auction start')
    ax2.set_ylabel('Price per 1e18 tokens (log scale)')
    ax2.set_title('Dutch Auction Price Decay Comparison - Logarithmic Scale')
    ax2.set_yscale('log')
    
    # Set y-axis limits to show full decimal range
    if all_prices:
        min_price = min(all_prices)
        max_price = max(all_prices)
        ax2.set_ylim(min_price * 0.1, max_price * 10)  # Add some margin
    
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add vertical lines to show auction end times
    ax2.axvline(x=24, color='gray', linestyle='--', alpha=0.5, label='24h mark')
    ax2.axvline(x=36, color='gray', linestyle='--', alpha=0.5, label='36h mark')
    
    # Add some styling
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('price_decay_comparison.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'price_decay_comparison.png'")
    
    # Create rich formatted table
    console = Console()
    
    # Calculate prices at different time points (sample 1 second before target to get final price)
    def get_price_at_time(auction, from_token, target_hours):
        """Get price 1 second before target time to capture final price before auction ends"""
        target_seconds = target_hours * 3600 - 1  # 1 second before target
        kicked_time = auction.kicked(from_token.address)
        timestamp = int(kicked_time + target_seconds)
        
        try:
            price = auction.price(from_token.address, timestamp) / 1e18
            return price if price > 0 else None
        except:
            return None
    
    # Get prices at specific time points (1 second before target to capture final prices)
    price_12h_half_life = get_price_at_time(half_life_auction, from_token, 12)
    price_12h_extended = get_price_at_time(extended_auction, from_token, 12)
    price_12h_fixed = get_price_at_time(fixed_auction, from_token, 12)
    price_12h_fixed_24s = get_price_at_time(fixed_24s_auction, from_token, 12)
    price_12h_custom = get_price_at_time(custom_auction, from_token, 12)
    
    price_24h_half_life = get_price_at_time(half_life_auction, from_token, 24)
    price_24h_extended = get_price_at_time(extended_auction, from_token, 24)
    price_24h_fixed = get_price_at_time(fixed_auction, from_token, 24)
    price_24h_fixed_24s = get_price_at_time(fixed_24s_auction, from_token, 24)
    price_24h_custom = get_price_at_time(custom_auction, from_token, 24)
    
    price_36h_half_life = get_price_at_time(half_life_auction, from_token, 36)
    price_36h_extended = get_price_at_time(extended_auction, from_token, 36)
    price_36h_fixed = get_price_at_time(fixed_auction, from_token, 36)
    price_36h_fixed_24s = get_price_at_time(fixed_24s_auction, from_token, 36)
    price_36h_custom = get_price_at_time(custom_auction, from_token, 36)
    
    # Get actual deployed contract parameters (starting prices)
    def get_starting_price(prices):
        for price in prices:
            if price is not None:
                return price
        return 0
    
    half_life_starting = get_starting_price(half_life_prices)
    extended_starting = get_starting_price(extended_prices)
    fixed_starting = get_starting_price(fixed_prices)
    fixed_24s_starting = get_starting_price(fixed_24s_prices)
    custom_starting = get_starting_price(custom_prices)
    
    # Create the table
    table = Table(title="🔨 Dutch Auction Parameters & 24h Results (Fork Deploy Sim)", title_style="bold magenta")
    
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Duration", style="magenta")
    table.add_column("Decay Rate", style="yellow")
    table.add_column("Update Interval", style="green")
    table.add_column("Starting Price", style="blue")
    table.add_column("Price @ 12h", style="bright_yellow")
    table.add_column("Price @ 24h", style="red")
    table.add_column("Price @ 36h", style="bright_red")
    
    # Add rows for each auction type
    table.add_row(
        "1", 
        "24h",
        f"-{(1-custom_decay)*100:.2f}%/step",
        f"{custom_interval}s",
        f"{custom_starting:,.2f}",
        f"{price_12h_custom:,.2f}" if price_12h_custom is not None else "ended",
        f"{price_24h_custom:,.2f}" if price_24h_custom is not None else "ended",
        f"{price_36h_custom:,.2f}" if price_36h_custom is not None else "ended",
        style="blue"
    )
    
    table.add_row(
        "2",
        "24h",
        f"-{(1-half_life_decay)*100:.2f}%/step",
        f"{half_life_interval}s",
        f"{half_life_starting:,.2f}",
        f"{price_12h_half_life:,.2f}" if price_12h_half_life is not None else "ended",
        f"{price_24h_half_life:,.2f}" if price_24h_half_life is not None else "ended",
        f"{price_36h_half_life:,.2f}" if price_36h_half_life is not None else "ended",
        style="red"
    )
    
    table.add_row(
        "3",
        "36h",
        f"-{(1-extended_decay)*100:.2f}%/step", 
        f"{extended_interval}s",
        f"{extended_starting:,.2f}",
        f"{price_12h_extended:,.2f}" if price_12h_extended is not None else "ended",
        f"{price_24h_extended:,.2f}" if price_24h_extended is not None else "ended",
        f"{price_36h_extended:,.2f}" if price_36h_extended is not None else "ended",
        style="green"
    )
    
    table.add_row(
        "4",
        "24h",
        f"-{(1-fixed_decay)*100:.2f}%/step",
        f"{fixed_interval}s",
        f"{fixed_starting:,.2f}",
        f"{price_12h_fixed:,.2f}" if price_12h_fixed is not None else "ended",
        f"{price_24h_fixed:,.2f}" if price_24h_fixed is not None else "ended",
        f"{price_36h_fixed:,.2f}" if price_36h_fixed is not None else "ended",
        style="bright_yellow"
    )
    
    table.add_row(
        "5",
        "24h",
        f"-{(1-fixed_24s_decay)*100:.2f}%/step",
        f"{fixed_24s_interval}s",
        f"{fixed_24s_starting:,.2f}",
        f"{price_12h_fixed_24s:,.2f}" if price_12h_fixed_24s is not None else "ended",
        f"{price_24h_fixed_24s:,.2f}" if price_24h_fixed_24s is not None else "ended",
        f"{price_36h_fixed_24s:,.2f}" if price_36h_fixed_24s is not None else "ended",
        style="magenta"
    )
    
    console.print("\n")
    console.print(table)
    console.print("\n")
    
    # Show the plot
    plt.show()
    
    # Print additional statistics
    print(f"=== BLOCKCHAIN DEPLOYED AUCTION ANALYSIS ===")
    print(f"All prices calculated from actual deployed contracts")
    
    print(f"\nStarting Prices:")
    print(f"  Half-Life: {half_life_starting:,.0f}")
    print(f"  Extended:  {extended_starting:,.0f}")
    print(f"  Fixed:     {fixed_starting:,.0f}")
    print(f"  Custom:    {custom_starting:,.0f}")
    
    return half_life_prices, extended_prices, fixed_prices, custom_prices, hours

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