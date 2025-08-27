# Dutch Auction Price Decay Experiment

This project compares multiple Dutch auction price decay mechanisms using a flexible Solidity smart contract and Python analysis.

## Setup

### Install Dependencies

```bash
pip3 install eth-brownie matplotlib numpy rich
```

## Running the Project

### Run Analysis

```bash
# Run full blockchain analysis with deployment and visualization
brownie run analyze_price_decay
```

This will:

- Deploy 5 different auction configurations
- Generate a comparison chart (`price_decay_comparison.png`)
- Display detailed auction parameters and price snapshots

## Updating Parameters

To experiment with different auction behaviors, modify the parameters in `scripts/analyze_price_decay.py`:

- **Price Update Intervals**: How frequently prices update (in seconds)
- **Decay Rates**: The percentage price decreases per step
- **Starting Prices**: Initial auction prices
- **Auction Duration**: How long auctions run

The project uses a single `ParameterizedAuction.sol` contract that accepts constructor parameters to create different auction types, making it easy to test various configurations.
