# Dutch Auction Price Decay Experiment

This project compares two different price decay mechanisms for Dutch auctions using Solidity smart contracts and Python analysis.

## Project Structure

```
├── contracts/
│   ├── Auction.sol              # Original Yearn auction contract
│   ├── ModifiedAuction.sol      # Modified contract with step-based decay
│   ├── interfaces/
│   ├── libraries/
│   └── utils/
├── scripts/
│   ├── deploy.py                # Deployment script for both contracts
│   ├── analyze_price_decay.py   # Full blockchain analysis (requires network)
│   └── simulate_price_decay.py  # Mathematical simulation (standalone)
├── brownie-config.yaml          # Brownie configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Price Decay Mechanisms

### Original Auction (Exponential Decay)
- Uses Ajna finance's exponential step decay
- Price halves every hour with minute-level granularity
- Constants: `MINUTE_HALF_LIFE = 0.988514020352896135356867505` (0.5^(1/60))

### Modified Auction (Step-Based Decay)  
- Uses fixed 36-second intervals with discrete price updates
- Price decays by ~0.69% every 36 seconds
- Constants: `PRICE_UPDATE_INTERVAL = 36s`, `STEP_DECAY = 0.993092495437035901533210216` (0.5^(1/100))

## Results

Both mechanisms achieve approximately 50% price reduction per hour, but with different granularity:

- **Original**: Smooth exponential decay with minute-level updates
- **Modified**: Step-based decay with 36-second intervals (100 steps per hour)

### Key Findings
- Starting price: 1,000,000 tokens
- After 1 hour: ~500,000 tokens (50% of start)
- After 6 hours: ~15,625 tokens (1.56% of start) 
- After 12 hours: ~244 tokens (0.02% of start)
- After 24 hours: ~0.06 tokens (0.000006% of start)

## Usage

### Option 1: Mathematical Simulation (Recommended)
```bash
# Install dependencies
pip3 install matplotlib numpy

# Run simulation
python3 scripts/simulate_price_decay.py
```

### Option 2: Full Blockchain Analysis
```bash
# Install brownie
pip3 install eth-brownie

# Run analysis with blockchain deployment
brownie run analyze_price_decay
```

## Generated Output

The simulation produces:
- `price_decay_simulation.png`: Comparison chart showing both decay mechanisms
- Console output with detailed statistics and step behavior analysis

## Contract Details

Both contracts implement the same interface but use different `_price()` functions:

- **Starting Price**: 1M tokens (configurable)
- **Auction Length**: 24 hours (86400 seconds)
- **Token Amount**: 1e18 tokens being auctioned

The modified version specifically implements 36-second step intervals designed to create 100 price update steps per hour, maintaining the same overall decay rate as the original exponential function.