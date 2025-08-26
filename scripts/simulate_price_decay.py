#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import math

def minute_step_price_function(seconds_elapsed, starting_price, available_tokens, auction_length):
    """
    Minute-step auction price function (original Yearn implementation)
    Based on Ajna finance implementation with minute-level updates
    """
    if available_tokens == 0 or seconds_elapsed > auction_length:
        return 0
    
    # Constants from original contract
    MINUTE_HALF_LIFE = 0.988514020352896135356867505  # 0.5^(1/60) 
    
    # Exponential step decay
    hours_component = 1.0 / (2 ** (seconds_elapsed // 3600))  # 1e27 >> (secondsElapsed / 3600)
    minutes_component = MINUTE_HALF_LIFE ** ((seconds_elapsed % 3600) // 60)
    
    # Initial price calculation
    initial_price = (starting_price * 1e18) / available_tokens
    
    # Final price with decay
    price = initial_price * hours_component * minutes_component
    
    return price / 1e18  # Scale back to readable units

def medium_step_price_function(seconds_elapsed, starting_price, available_tokens, auction_length):
    """
    Medium-step auction price function with 36-second intervals
    """
    if available_tokens == 0 or seconds_elapsed > auction_length:
        return 0
    
    # Medium step constants
    PRICE_UPDATE_INTERVAL = 36  # seconds
    STEP_DECAY = 0.993092495437035901533210216  # 0.5^(1/100) in decimal
    
    # Total number of 36s steps since auction started
    steps_elapsed = seconds_elapsed // PRICE_UPDATE_INTERVAL
    
    # Calculate decay: STEP_DECAY^steps_elapsed
    decay = STEP_DECAY ** steps_elapsed
    
    # Initial price calculation  
    initial_price = (starting_price * 1e18) / available_tokens
    
    # Final price with step decay
    price = initial_price * decay
    
    return price / 1e18  # Scale back to readable units

def small_step_price_function(seconds_elapsed, starting_price, available_tokens, auction_length):
    """
    Small-step auction price function with 36-second intervals for 36-hour auctions
    Same final price as 24h auction but extended over 36 hours
    """
    if available_tokens == 0 or seconds_elapsed > auction_length:
        return 0
    
    # Small step constants  
    PRICE_UPDATE_INTERVAL = 36  # seconds
    # Option 2: (0.5^24)^(1/3600) = 0.5^(1/150)
    STEP_DECAY = 0.995389679103229139420708864  # Same final price as 24h auction
    
    # Total number of 36s steps since auction started
    steps_elapsed = seconds_elapsed // PRICE_UPDATE_INTERVAL
    
    # Calculate decay: STEP_DECAY^steps_elapsed
    decay = STEP_DECAY ** steps_elapsed
    
    # Initial price calculation  
    initial_price = (starting_price * 1e18) / available_tokens
    
    # Final price with step decay
    price = initial_price * decay
    
    return price / 1e18  # Scale back to readable units

def plot_price_comparison():
    """Plot and compare all three price decay functions"""
    
    # Parameters
    starting_price = 1_000_000 * 1e18  # 1M tokens
    available_tokens = 1e18  # 1e18 tokens available
    
    # Different auction lengths for comparison
    standard_length = 24 * 3600  # 24 hours in seconds
    extended_length = 36 * 3600  # 36 hours in seconds
    
    # Time points for plotting (show 36 hours to see small step completion)
    time_points = np.linspace(0, 36 * 3600, 36 * 60)  # Every minute for 36 hours
    hours = time_points / 3600  # Convert to hours for plotting
    
    # Calculate prices for all three auctions
    minute_step_prices = []
    medium_step_prices = []
    small_step_prices = []
    
    print("Calculating price curves for all three auction types...")
    for t in time_points:
        # Minute-step and medium-step use 24-hour length
        minute_price = minute_step_price_function(int(t), starting_price, available_tokens, standard_length)
        medium_price = medium_step_price_function(int(t), starting_price, available_tokens, standard_length)
        
        # Small-step uses 36-hour length
        small_price = small_step_price_function(int(t), starting_price, available_tokens, extended_length)
        
        minute_step_prices.append(minute_price)
        medium_step_prices.append(medium_price)
        small_step_prices.append(small_price)
    
    # Calculate step sizes (percentage price change per update)
    # For minute-step: 60s intervals, MINUTE_HALF_LIFE per 60s
    minute_step_change = (1 - 0.988514020352896135356867505) * 100  # % change per minute
    
    # For medium-step: 36s intervals, 0.5^(1/100) per 36s  
    medium_step_change = (1 - 0.993092495437035901533210216) * 100  # % change per 36s
    
    # For small-step: 36s intervals, 0.5^(1/150) per 36s
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
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('price_decay_simulation.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'price_decay_simulation.png'")
    
    # Print statistics
    print(f"\n=== PRICE DECAY ANALYSIS ===")
    print(f"Starting price (all): {minute_step_prices[0]:.6f}")
    
    print(f"\nAfter 1 hour:")
    idx_1h = 1 * 60
    print(f"  Minute-Step: {minute_step_prices[idx_1h]:.6f} ({minute_step_prices[idx_1h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Medium-Step: {medium_step_prices[idx_1h]:.6f} ({medium_step_prices[idx_1h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Small-Step:  {small_step_prices[idx_1h]:.6f} ({small_step_prices[idx_1h]/minute_step_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 6 hours:")
    idx_6h = 6 * 60
    print(f"  Minute-Step: {minute_step_prices[idx_6h]:.6f} ({minute_step_prices[idx_6h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Medium-Step: {medium_step_prices[idx_6h]:.6f} ({medium_step_prices[idx_6h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Small-Step:  {small_step_prices[idx_6h]:.6f} ({small_step_prices[idx_6h]/minute_step_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 12 hours:")
    idx_12h = 12 * 60
    print(f"  Minute-Step: {minute_step_prices[idx_12h]:.6f} ({minute_step_prices[idx_12h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Medium-Step: {medium_step_prices[idx_12h]:.6f} ({medium_step_prices[idx_12h]/minute_step_prices[0]*100:.2f}% of start)")
    print(f"  Small-Step:  {small_step_prices[idx_12h]:.6f} ({small_step_prices[idx_12h]/minute_step_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 24 hours:")
    idx_24h = 24 * 60
    print(f"  Minute-Step: {minute_step_prices[idx_24h]:.8f} ({minute_step_prices[idx_24h]/minute_step_prices[0]*100:.6f}% of start)")
    print(f"  Medium-Step: {medium_step_prices[idx_24h]:.8f} ({medium_step_prices[idx_24h]/minute_step_prices[0]*100:.6f}% of start)")
    print(f"  Small-Step:  {small_step_prices[idx_24h]:.2f} ({small_step_prices[idx_24h]/minute_step_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 36 hours:")
    idx_36h = 36 * 60
    print(f"  Minute-Step: Ended at 24h")
    print(f"  Medium-Step: Ended at 24h") 
    print(f"  Small-Step:  {small_step_prices[idx_36h]:.8f} ({small_step_prices[idx_36h]/minute_step_prices[0]*100:.6f}% of start)")
    
    # Show step granularity comparison
    print(f"\n=== STEP GRANULARITY COMPARISON (First 2 minutes) ===")
    for i in range(0, min(121, len(time_points))):
        t_sec = int(time_points[i] / 60)  # Convert to minutes
        if t_sec % 0.5 == 0 and t_sec <= 2:  # Every 30 seconds for first 2 minutes
            t_min = t_sec
            idx = int(t_sec * 60)  # Convert back to index
            if idx < len(minute_step_prices):
                print(f"  {t_min:3.1f} min: Minute={minute_step_prices[idx]:.0f}, Medium={medium_step_prices[idx]:.0f}, Small={small_step_prices[idx]:.0f}")
    
    plt.show()
    
    return minute_step_prices, medium_step_prices, small_step_prices, hours

def main():
    """Main function"""
    try:
        plot_price_comparison()
        print("\nAnalysis complete! Check the generated plot.")
    except Exception as e:
        print(f"Error during simulation: {str(e)}")
        print("Make sure you have matplotlib and numpy installed:")
        print("pip install matplotlib numpy")

if __name__ == "__main__":
    main()