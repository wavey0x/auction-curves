# Auction System 🏛️

A comprehensive Dutch auction monitoring system with multi-chain support, real-time dashboard, and smart contract deployment tools.

## 🚀 Quick Start (30 seconds)

**Just want to see the UI?**

```bash
git clone <repo-url>
cd auction-system
./run.sh mock
```

Open **http://localhost:3000** 🎉

## 📋 Prerequisites

- **Node.js 18+** and **Python 3.9+**
- **Docker** (for development mode)
- **Brownie, Foundry, Rindexer** (for development mode)

## 🎯 Operating Modes

The system supports three modes via a single unified script:

### 🎭 Mock Mode - UI Testing (10 seconds)
Perfect for frontend development and demos
```bash
./run.sh mock
```
- ✅ Hardcoded realistic test data
- ✅ No blockchain/database required  
- ✅ All networks supported with mock data
- 🌐 **Access**: http://localhost:3000

### 🔧 Development Mode - Full Stack (60 seconds)  
Complete local blockchain simulation
```bash
./run.sh dev
```
- ✅ Local Anvil blockchain + PostgreSQL
- ✅ Smart contract auto-deployment
- ✅ Real-time event indexing with Rindexer
- ✅ Price monitoring and activity simulation
- 🌐 **Access**: http://localhost:3000 (UI), http://localhost:8000/docs (API)

### 🚀 Production Mode - Multi-Network (2-5 minutes)
Production deployment with real blockchain networks
```bash
./run.sh prod
# or server-only: ./run.sh prod --no-ui
```
- ✅ Ethereum, Polygon, Arbitrum, Optimism, Base
- ✅ Production database with real transaction data  
- ✅ Multi-network event indexing
- 🌐 **Access**: http://localhost:8000/docs (API)

## ⚙️ Configuration

### Single .env File
The system now uses **only two environment files**:
- `.env` - Your actual configuration (copy from `.env.example`)
- `.env.example` - Template with all configuration options

All modes use one `.env` file with mode-specific prefixes:

```bash
# Switch modes by changing this line:
APP_MODE=dev          # or 'mock' or 'prod'

# Development configuration (DEV_*)
DEV_DATABASE_URL=postgresql://postgres:password@localhost:5432/auction
DEV_NETWORKS_ENABLED=local

# Production configuration (PROD_*)  
PROD_DATABASE_URL=postgresql://user:pass@prod-host:5432/auction
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
PROD_ETHEREUM_FACTORY_ADDRESS=0x_YOUR_DEPLOYED_FACTORY
```

### Quick Mode Switching
```bash
./run.sh mock    # Temporary override
./run.sh dev     # or edit .env: APP_MODE=dev  
./run.sh prod    # for persistent setting
```

> **Note**: No more multiple `.env.development`, `.env.production`, `.env.mock` files! The unified system uses mode-specific prefixes (`DEV_*`, `MOCK_*`, `PROD_*`) in a single `.env` file.

## 🏗️ Architecture

### Smart Contracts (`/contracts/core/`)
- **Auction.sol**: Main Dutch auction contract (configurable decay parameters)
- **AuctionFactory.sol**: Factory for deploying auction instances  
- **Libraries**: Maths calculations and governance utilities

### Backend (`/monitoring/api/`)
- **Production API**: `app.py` - Full database + blockchain integration
- **Mock API**: `simple_server.py` - Hardcoded data for UI testing
- **Database**: PostgreSQL with TimescaleDB for time-series optimization

### Frontend (`/ui/`)
- **React 18** with **TypeScript** and **Vite**
- **TailwindCSS** dark theme design system
- **@tanstack/react-query** for server state management
- **Real-time polling** for live auction updates

### Deployment Options

**Development**: Everything runs locally with optional Docker for database
**Free Hosting**: Designed for zero-cost deployment on platforms like Vercel
**Enterprise**: Full Docker containerization with Kubernetes support

### Indexing (`/indexer/rindexer/`)
- **Multi-network configuration**: Local, mainnet, L2 chains
- **Automatic event processing**: Kicks, takes, deployments
- **Database integration**: Events stored with chain_id for multi-chain support
- **Dynamic contract discovery**: Factory pattern automatically discovers all deployed auctions

#### Dynamic Contract Discovery
The indexer uses Rindexer's factory pattern to automatically discover and index new auction contracts without manual configuration:

1. **Factory Contracts**: Each network has one or more factory contracts that deploy auction instances
2. **Automatic Discovery**: When a factory emits `DeployedNewAuction`, Rindexer automatically starts indexing that new auction contract
3. **Zero Configuration**: No need to hardcode auction addresses - the system scales automatically as new auctions are deployed
4. **Multi-Network**: Works across all supported networks (Ethereum, Polygon, Arbitrum, Optimism, Base) with unified database storage

**Benefits**: Deploy unlimited factories → Deploy unlimited auctions → Automatic indexing with zero configuration drift

## 🗄️ Database Schema

**Multi-chain native design** - all tables include `chain_id`:

- **auctions**: Contract metadata per chain
- **auction_rounds**: Round tracking with incremental IDs
- **auction_sales**: Individual takes with sequence numbers
- **tokens**: ERC20 metadata cache across chains
- **price_history**: Time-series price data (TimescaleDB optimized)

## 📊 API Endpoints

### Core Endpoints
```
GET  /auctions                          # List all auctions with filtering
GET  /auctions/{address}                # Individual auction details
GET  /auctions/{address}/rounds         # Historical rounds  
GET  /auctions/{address}/sales          # Sales/take events
GET  /health                           # System health check
GET  /docs                             # Interactive API documentation
```

### Multi-Chain Support
```
GET  /chains                           # Supported blockchain networks
GET  /chains/{chainId}                 # Specific chain information
```

## 🛠️ Development Workflow

### Adding New Features
```bash
# 1. Start with mock mode for UI development
./run.sh mock

# 2. Test with full stack once UI is ready
./run.sh dev

# 3. Deploy to production when tested
./run.sh prod
```

### Common Tasks
```bash
# View logs and status
./run.sh dev         # Shows loaded configuration

# Health checks  
curl http://localhost:8000/health
curl http://localhost:8000/networks

# Stop all services
Ctrl+C               # Automatically cleans up all processes
```

## 🔍 Monitoring & Health

### Built-in Monitoring
- **API Health**: `/health` endpoint for service status
- **Network Status**: `/networks` for blockchain connectivity
- **Live Dashboard**: Real-time auction activity and charts
- **Database Metrics**: Performance tracking via TimescaleDB

### Production Monitoring
```bash
# Check all networks
curl http://localhost:8000/networks | jq

# Monitor specific chain
curl http://localhost:8000/networks/ethereum | jq

# View auction activity  
curl http://localhost:8000/auctions | jq
```

## 🚀 Deployment Examples

### Local Development
```bash
git clone <repo-url>
cd auction-system
./run.sh dev
# → Full development stack ready in ~60 seconds
```

### Production Setup
```bash
# 1. Configure production in .env:
APP_MODE=prod
PROD_DATABASE_URL=postgresql://user:pass@prod-db:5432/auction
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
PROD_ETHEREUM_FACTORY_ADDRESS=0x_YOUR_DEPLOYED_FACTORY

# 2. Deploy:
./run.sh prod

# 3. Monitor:
curl http://localhost:8000/networks
```

## 🏆 Key Features

### 🎯 **Easy Deployment**
- Single script handles all complexity
- Three modes cover all use cases  
- Automatic dependency validation
- Health checks and error reporting

### 📊 **Real-Time Monitoring**
- Live price tracking across all chains
- Interactive dashboards with progress bars
- Multi-network activity aggregation
- Historical analytics and charts

### 🧪 **Developer Friendly**
- Mock mode for instant UI feedback
- TypeScript throughout for type safety
- Hot reload for rapid iteration
- Comprehensive error handling

### 🌐 **Multi-Chain Native**
- Ethereum, Polygon, Arbitrum, Optimism, Base
- Chain-specific transaction links
- Network health monitoring
- Unified API across all chains

## 🆘 Troubleshooting

### Common Issues
```bash
# Port conflicts  
lsof -i :3000 :8000 :8545    # Check what's using ports
kill -9 <PID>                # Kill conflicting process

# Environment issues
source .env && echo "✅ .env OK" || echo "❌ .env has errors"

# Service status
curl http://localhost:8000/health
```

### Mode-Specific Issues
- **Mock Mode**: Should always work (no external dependencies)
- **Dev Mode**: Check Docker is running (`docker ps`)
- **Prod Mode**: Verify RPC URLs and database connectivity

### Getting Help
```bash
./run.sh --help              # Show all options
curl http://localhost:8000/docs   # API documentation
```

## 📁 Project Structure

```
/
├── contracts/core/          # Solidity smart contracts
├── ui/                     # React TypeScript frontend
├── monitoring/api/         # FastAPI backend (production + mock)
├── indexer/rindexer/       # Multi-network blockchain indexing
├── data/postgres/          # Database schema and migrations
├── scripts/                # Deployment and utility scripts
├── .env                    # Unified configuration file
├── .env.example            # Configuration template  
└── run.sh                  # Single deployment script
```

## 📚 Documentation

### Project Documentation
- **[RUN_GUIDE.md](RUN_GUIDE.md)**: Detailed setup and configuration guide
- **[FREE_HOSTING.md](FREE_HOSTING.md)**: Zero-cost deployment guide for Vercel, Supabase, etc.
- **[MODES.md](MODES.md)**: Complete mode documentation with examples
- **[architecture.md](architecture.md)**: Full system architecture overview
- **[CLAUDE.md](CLAUDE.md)**: LLM-optimized development guide

### External Documentation
- **[Rindexer Factory Pattern](https://rindexer.xyz/docs/start-building/yaml-config/contracts#factory)**: Dynamic contract discovery configuration
- **[Rindexer Configuration](https://rindexer.xyz/docs/start-building/yaml-config)**: Complete YAML configuration reference

## 🎯 Quick Reference

| Mode | Command | Time | Best For |
|------|---------|------|----------|
| **Demo** | `./run.sh mock` | 10s | UI testing, demos |
| **Development** | `./run.sh dev` | 60s | Full-stack development |
| **Production** | `./run.sh prod` | 5m | Real deployments |

**Stop any mode**: `Ctrl+C` (automatically cleans up all services)

---

**Built for the DeFi community** - Ready to monitor Dutch auctions across all major networks! 🚀