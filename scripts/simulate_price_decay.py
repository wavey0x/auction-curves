#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import math

def original_price_function(seconds_elapsed, starting_price, available_tokens, auction_length):
    """
    Original auction price function using exponential decay
    Based on Ajna finance implementation
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

def modified_price_function(seconds_elapsed, starting_price, available_tokens, auction_length):
    """
    Modified auction price function using step-based decay
    """
    if available_tokens == 0 or seconds_elapsed > auction_length:
        return 0
    
    # New constants
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

def plot_price_comparison():
    """Plot and compare both price decay functions"""
    
    # Parameters
    starting_price = 1_000_000 * 1e18  # 1M tokens
    available_tokens = 1e18  # 1e18 tokens available
    auction_length = 24 * 3600  # 24 hours in seconds
    
    # Time points (every minute for 24 hours)
    time_points = np.linspace(0, 24 * 3600, 24 * 60)
    hours = time_points / 3600  # Convert to hours for plotting
    
    # Calculate prices
    original_prices = []
    modified_prices = []
    
    print("Calculating price curves...")
    for t in time_points:
        original_price = original_price_function(int(t), starting_price, available_tokens, auction_length)
        modified_price = modified_price_function(int(t), starting_price, available_tokens, auction_length)
        
        original_prices.append(original_price)
        modified_prices.append(modified_price)
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    plt.plot(hours, original_prices, label='Original Auction (60-second steps)', linewidth=2, color='blue')
    plt.plot(hours, modified_prices, label='Modified Auction (36-second steps)', linewidth=2, color='red')
    
    plt.xlabel('Hours since auction start')
    plt.ylabel('Price per 1e18 tokens')
    plt.title('Dutch Auction Price Decay Comparison - Full 24 Hours')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('price_decay_simulation.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'price_decay_simulation.png'")
    
    # Print statistics
    print(f"\n=== PRICE DECAY ANALYSIS ===")
    print(f"Starting price (both): {original_prices[0]:.6f}")
    print(f"\nAfter 1 hour:")
    print(f"  Original: {original_prices[60]:.6f} ({original_prices[60]/original_prices[0]*100:.2f}% of start)")
    print(f"  Modified: {modified_prices[60]:.6f} ({modified_prices[60]/original_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 6 hours:")
    idx_6h = 6 * 60
    print(f"  Original: {original_prices[idx_6h]:.6f} ({original_prices[idx_6h]/original_prices[0]*100:.2f}% of start)")
    print(f"  Modified: {modified_prices[idx_6h]:.6f} ({modified_prices[idx_6h]/original_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 12 hours:")
    idx_12h = 12 * 60
    print(f"  Original: {original_prices[idx_12h]:.6f} ({original_prices[idx_12h]/original_prices[0]*100:.2f}% of start)")
    print(f"  Modified: {modified_prices[idx_12h]:.6f} ({modified_prices[idx_12h]/original_prices[0]*100:.2f}% of start)")
    
    print(f"\nAfter 24 hours:")
    print(f"  Original: {original_prices[-1]:.6f} ({original_prices[-1]/original_prices[0]*100:.6f}% of start)")
    print(f"  Modified: {modified_prices[-1]:.6f} ({modified_prices[-1]/original_prices[0]*100:.6f}% of start)")
    
    # Show step behavior of modified auction
    print(f"\n=== STEP BEHAVIOR ANALYSIS (First 10 minutes) ===")
    for i in range(0, min(11, len(time_points))):
        t_sec = int(time_points[i])
        if t_sec % 300 == 0:  # Every 5 minutes
            t_min = t_sec // 60
            print(f"  {t_min:2d} min: Original={original_prices[i]:.6f}, Modified={modified_prices[i]:.6f}")
    
    plt.show()
    
    return original_prices, modified_prices, hours

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