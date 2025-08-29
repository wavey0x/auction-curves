# Auction House 🏛️

A comprehensive monorepo containing a starter kit for anyone looking to use Dutch auctions, including deployment tools, monitoring infrastructure, and simulation capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone and setup**
   ```bash
   git clone <repo-url>
   cd auction-house
   ```

2. **Start infrastructure**
   ```bash
   docker-compose up postgres redis
   ```

3. **Setup database**
   ```bash
   python setup.py
   ```

4. **Deploy contracts locally**
   ```bash
   # Start Anvil (or use docker-compose up anvil)
   anvil --host 0.0.0.0

   # Generate ABIs for Rindexer
   brownie run scripts/generate_abis.py

   # Deploy factory and sample auctions
   brownie run scripts/deploy/factory.py --network development
   ```

5. **Start indexing**
   ```bash
   # Set environment variables
   export FACTORY_ADDRESS=<deployed_factory_address>
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/auction_house"
   
   # Start Rindexer (will auto-create event tables)
   cd indexer/rindexer
   rindexer start
   ```

## 📁 Project Structure

```
auction-house/
├── contracts/              # Smart contracts
│   ├── core/              # Main auction contracts
│   ├── interfaces/        # Contract interfaces  
│   └── test/             # Test contracts
├── scripts/              # Python automation
│   ├── deploy/          # Deployment scripts
│   ├── simulate/        # Simulation tools
│   └── monitor/         # Monitoring services
├── indexer/             # Blockchain event indexing
│   └── rindexer/       # Rindexer configuration
├── monitoring/          # Web dashboard
│   ├── frontend/       # React UI
│   └── api/           # FastAPI backend
├── data/               # Data infrastructure
│   ├── postgres/      # Database schemas
│   └── redis/        # Cache configs
└── docs/              # Documentation
```

## 🔧 Core Components

### Smart Contracts

#### AuctionFactory.sol
Factory contract for deploying ParameterizedAuction contracts with various configurations:
- **Configurable decay rates**: Custom step decay rates for different price reduction curves
- **Custom auctions**: Full control over price update intervals and decay rates
- **Tracking**: Maintains registry of all deployed auctions

#### ParameterizedAuction.sol  
Configurable Dutch auction contract supporting:
- **Flexible decay**: Custom step intervals and decay percentages
- **Multiple tokens**: Support for any ERC20 token pairs
- **CoW Protocol**: Compatible with CoW Swap for MEV protection
- **Governance**: Admin controls for enabling/disabling auctions

### Key Features

#### 🎯 **Deployment Made Easy**
```python
# Deploy a standard linear auction
brownie run scripts/deploy/factory.py

# Or customize everything
factory.createParameterizedAuction(
    want_token="0x...",      # Payment token (USDC, WETH, etc.)
    receiver="0x...",        # Revenue recipient  
    governance="0x...",      # Admin address
    auction_length=86400,    # 24 hours
    starting_price=1000000,  # Starting price
    price_interval=60,       # Update every 60 seconds
    step_decay=995e25,       # 0.5% decay per step
    fixed_price=0           # 0 = dynamic pricing
)
```

#### 📊 **Comprehensive Monitoring** 
- Real-time price tracking for all active auctions
- Historical performance analytics
- Participant behavior analysis  
- Arbitrage opportunity detection

#### 🧪 **Advanced Simulation**
- Fork mainnet with Anvil for realistic testing
- Backtest different auction parameters
- Model various market conditions
- Performance comparison tools

#### 📈 **Rich Analytics**
- PostgreSQL + TimescaleDB for time-series data
- Real-time dashboards with price curves
- Auction performance metrics
- Participant leaderboards

## 🛠️ Configuration Examples

### Example Configurations
All AuctionHouses use standardized constants from the smart contract:
- **Step Duration**: 36 seconds per step (constant)
- **Auction Length**: 86400 seconds (24 hours, constant)
- **Step Decay Rate**: Configurable per auction house

### Fast Decay Configuration
- **Decay**: 1% per step (99% of previous price)
- **Use case**: Quick liquidation with rapid price discovery

### Moderate Decay Configuration  
- **Decay**: 0.5% per step (99.5% of previous price)
- **Use case**: Balanced auctions for regular trading

### Slow Decay Configuration
- **Decay**: 0.2% per step (99.8% of previous price)  
- **Use case**: Conservative price discovery for large positions

### Custom Configuration
```python
# 36-hour auction with 90-second intervals and 1.5% decay
factory.createParameterizedAuction(
    # ... other params ...
    auction_length=36 * 3600,           # 36 hours
    price_interval=90,                  # 90 second updates
    step_decay=985000000000000000000000000,  # 1.5% decay (RAY format)
    fixed_price=0                       # Dynamic starting price
)
```

## 🗄️ Database Architecture

The system uses a **hybrid approach** with Rindexer + custom analytics:

### **Rindexer Auto-Generated Tables**
- **deployed_new_auction**: Factory deployment events
- **auction_enabled**: Token enablement events  
- **auction_kicked**: Auction round starts
- **auction_disabled**: Token disablement events
- **updated_starting_price**: Price update events

### **Custom Analytics Tables**
- **auction_parameters**: Contract parameter cache
- **price_history**: Calculated price curves
- **auction_round_analytics**: Aggregated round metrics
- **tokens**: ERC20 token metadata cache

Rindexer handles all event storage automatically, while custom tables provide business intelligence and performance optimizations.

## 🌐 GraphQL API (Automatic)

Rindexer automatically provides a GraphQL API for all indexed events:

```graphql
# Query deployed auctions
query {
  deployed_new_auction {
    auction
    want
    block_number
    timestamp
  }
}

# Query auction kicks
query {
  auction_kicked {
    from_token
    available
    block_number
    timestamp
  }
}

# Query with filters
query {
  auction_enabled(where: {to_token: "0x..."}) {
    from_token
    to_token
    timestamp
  }
}
```

**Planned REST API** (custom FastAPI layer):
- `GET /auctions/` - Enhanced auction list with analytics
- `GET /auctions/{address}/price` - Real-time price calculation
- `GET /auctions/{address}/chart` - Price history visualization
- `WS /ws/auctions/{address}` - Real-time updates

## 🚀 Deployment

### Local Testing
```bash
# Start full stack
docker-compose --profile=blockchain --profile=api --profile=frontend up

# Deploy contracts  
brownie run scripts/deploy/factory.py --network mainnet-fork

# Start indexer
docker-compose --profile=indexer up
```

### Production
```bash
# Set environment variables
export DATABASE_URL="postgresql://..."
export REDIS_URL="redis://..."
export MAINNET_RPC_URL="https://..."

# Deploy infrastructure
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- [Architecture Overview](docs/architecture.md) 
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Configuration Options](docs/configuration.md)
- [Example Strategies](docs/examples/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## ⚖️ License

This project is licensed under AGPL-3.0 - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Yearn Finance](https://yearn.fi) - Original auction contract inspiration
- [CoW Protocol](https://cow.fi) - MEV protection integration
- [Brownie Framework](https://eth-brownie.readthedocs.io) - Smart contract development
- [Rindexer](https://rindexer.xyz) - Blockchain event indexing

---

**Built with ❤️ for the DeFi community**

*Ready to auction anything, anytime, anywhere.*