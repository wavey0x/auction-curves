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
- **Brownie, Foundry** (for development mode)

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
- ✅ Real-time event indexing with custom Web3.py indexer
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
- ✅ Multi-network event indexing with custom Web3.py indexer
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

#### Dynamic Contract Configuration (Dev Mode)
In development mode, the indexer configuration is generated dynamically to match deployed contracts:

1. **Template-Based**: Uses `rindexer.template.yaml` with placeholder addresses
2. **Post-Deployment Generation**: After contracts deploy, `deployment_info.json` is used to generate `rindexer-dev.yaml`
3. **Fresh State**: Rindexer internal state is cleaned on each dev run for consistent testing
4. **Hardcoded Addresses**: Generated config uses actual deployed addresses, avoiding environment variable expansion issues

**Why Dynamic Generation?**
- Rindexer environment variable expansion (`${VAR}`) has parsing issues
- Factory-based auto-discovery causes panics in current Rindexer version
- Development needs fresh, reproducible environments
- Generated config ensures accurate indexing of deployed contracts

**Benefits**: Deploy unlimited factories → Deploy unlimited auctions → Automatic indexing with zero configuration drift

## 🗄️ Database Schema

**Multi-chain native design** - all tables include `chain_id`:

- **auctions**: Contract metadata per chain
- **auction_rounds**: Round tracking with incremental IDs
- **auction_sales**: Individual takes with sequence numbers
- **tokens**: ERC20 metadata cache across chains
- **price_history**: Time-series price data (TimescaleDB optimized)

## 📊 API Endpoints

### Core Auction Endpoints
```
GET  /auctions                                           # List auctions with filtering (status, page, limit, chain_id)
GET  /auctions/{chain_id}/{auction_address}             # Individual auction details  
GET  /auctions/{chain_id}/{auction_address}/takes       # Get takes for specific auction (with round filtering)
GET  /auctions/{chain_id}/{auction_address}/rounds      # Get auction round history (with token filtering)
GET  /auctions/{chain_id}/{auction_address}/price-history # Price history for charting (placeholder)
```

### Taker Analytics Endpoints
```
GET  /takers                                            # List takers ranked by activity (volume/takes/recent)
GET  /takers/{taker_address}                           # Detailed taker profile with rankings
GET  /takers/{taker_address}/takes                     # Paginated takes history for specific taker
GET  /takers/{taker_address}/token-pairs               # Most frequented token pairs by taker
```

### System & Network Endpoints
```
GET  /                                                 # API root with status and endpoint listing
GET  /health                                          # System health check with database status
GET  /system/stats                                    # System statistics (with optional chain filtering)
GET  /tokens                                          # Token registry across all chains
GET  /chains                                          # Supported blockchain networks with metadata
GET  /chains/{chain_id}                               # Specific chain information
GET  /networks                                        # Active network configurations and status
GET  /networks/{network_name}                         # Detailed network information
```

### Activity & Analytics Endpoints  
```
GET  /activity/takes                                   # Recent takes across all auctions (most recent first)
GET  /activity/kicks                                   # Legacy kicks endpoint (placeholder)
GET  /analytics/overview                               # System overview with legacy format compatibility
```

### API Documentation
```
GET  /docs                                            # Interactive Swagger documentation
GET  /redoc                                           # ReDoc API documentation
```

## 📋 API Documentation Details

### Auction Endpoints

**GET `/auctions`** - List auctions with filtering
- **Parameters**: 
  - `status` (string): Filter by "all", "active", or "completed" (default: "all")
  - `page` (int): Page number (default: 1, min: 1)
  - `limit` (int): Items per page (default: 20, max: 100)
  - `chain_id` (int): Filter by specific chain ID (optional)
- **Response**: Paginated list of auctions with metadata

**GET `/auctions/{chain_id}/{auction_address}`** - Get auction details
- **Parameters**: 
  - `chain_id` (int): Blockchain network ID (e.g., 1 for Ethereum)
  - `auction_address` (string): Contract address of the auction
- **Response**: Complete auction information including parameters and status

**GET `/auctions/{chain_id}/{auction_address}/takes`** - Get auction takes
- **Parameters**:
  - `round_id` (int): Filter by specific round ID (optional)
  - `limit` (int): Number of takes to return (default: 50, max: 100)
  - `offset` (int): Skip this many takes for pagination (default: 0)
- **Response**: List of takes/sales for the auction

**GET `/auctions/{chain_id}/{auction_address}/rounds`** - Get auction rounds  
- **Parameters**:
  - `from_token` (string): Filter by token being sold (optional)
  - `round_id` (int): Get specific round ID (optional)
  - `limit` (int): Number of rounds to return (default: 50, max: 100)
- **Response**: Historical round data with pricing and timing

### Taker Analytics Endpoints

**GET `/takers`** - List and rank takers by activity
- **Parameters**:
  - `sort_by` (string): Sort by "volume", "takes", or "recent" (default: "volume")
  - `limit` (int): Number of takers per page (default: 25, max: 100)  
  - `page` (int): Page number (default: 1)
  - `chain_id` (int): Filter by specific chain (optional)
- **Response**: `TakerListResponse` with ranked taker summaries

**GET `/takers/{taker_address}`** - Get detailed taker profile
- **Parameters**: 
  - `taker_address` (string): Ethereum address of the taker wallet
- **Response**: `TakerDetail` with comprehensive statistics and auction breakdown

**GET `/takers/{taker_address}/takes`** - Get taker's take history
- **Parameters**:
  - `limit` (int): Takes per page (default: 20, max: 100)
  - `page` (int): Page number (default: 1)
- **Response**: `TakerTakesResponse` with paginated takes list

**GET `/takers/{taker_address}/token-pairs`** - Get frequented token pairs
- **Parameters**:
  - `page` (int): Page number (default: 1)
  - `limit` (int): Token pairs per page (default: 50, max: 100)
- **Response**: Token pairs ranked by frequency of takes

### System Information

**GET `/system/stats`** - System-wide statistics
- **Parameters**:
  - `chain_id` (int): Filter statistics by chain (optional)
- **Response**: `SystemStats` with auction counts, volumes, and activity metrics

**GET `/chains`** - Supported blockchain networks
- **Response**: Map of chain IDs to network metadata (name, explorer, icon)

**GET `/networks`** - Active network configurations
- **Response**: Current network status including RPC health and factory addresses

## 🏗️ Data Models & Response Structures

### Core Data Models

**TakerSummary** - Used in taker list views
```typescript
{
  taker: string;              // Taker wallet address
  total_takes: number;        // Total number of takes
  unique_auctions: number;    // Number of unique auctions participated in
  unique_chains: number;      // Number of chains active on
  total_volume_usd: string;   // Total USD volume (formatted string)
  avg_take_size_usd: string;  // Average USD per take (formatted string)
  first_take: datetime;       // Timestamp of first take
  last_take: datetime;        // Timestamp of most recent take
  active_chains: number[];    // Array of chain IDs where taker is active
  rank_by_takes: number;      // Rank position by total takes count
  rank_by_volume: number;     // Rank position by total USD volume
}
```

**TakerDetail** - Comprehensive taker profile
```typescript
{
  // All TakerSummary fields plus:
  auction_breakdown: AuctionBreakdown[];  // Per-auction activity breakdown
}
```

**AuctionBreakdown** - Taker's activity per auction
```typescript
{
  auction_address: string;    // Auction contract address
  chain_id: number;          // Chain ID
  takes_count: number;       // Number of takes in this auction
  volume_usd: string;        // Total USD volume in this auction
  last_take: datetime;       // Most recent take in this auction
}
```

**SystemStats** - System-wide statistics
```typescript
{
  total_auctions: number;     // Number of unique auctions
  total_takes: number;        // Total takes across all auctions
  total_volume_usd: string;   // Total USD volume (formatted)
  active_auctions: number;    // Currently active auctions
  unique_takers: number;      // Number of unique taker addresses
  supported_chains: number;   // Number of supported blockchain networks
}
```

### Response Wrappers

**TakerListResponse** - Paginated taker list
```typescript
{
  takers: TakerSummary[];     // Array of taker summaries
  total: number;              // Total number of takers
  page: number;               // Current page number
  per_page: number;           // Items per page
  has_next: boolean;          // Whether more pages exist
}
```

**TakerTakesResponse** - Paginated takes for specific taker
```typescript
{
  takes: Take[];              // Array of take objects
  total: number;              // Total takes by this taker
  page: number;               // Current page number
  per_page: number;           // Items per page
  has_next: boolean;          // Whether more pages exist
}
```

### Database Integration

The API uses **PostgreSQL with TimescaleDB** for optimal time-series performance:

- **Real-time USD calculations** via database views and LATERAL joins with token price data
- **Multi-chain support** with `chain_id` fields across all tables
- **Optimized indexes** for frequent queries (taker rankings, auction filtering)
- **Materialized views** for complex aggregations (taker statistics, system stats)

### Authentication & Rate Limiting

- **Public API**: No authentication required for read operations
- **CORS enabled** for frontend integration
- **Rate limiting**: Implemented at FastAPI level for production deployments
- **Health checks**: Built-in endpoints for monitoring and load balancer health checks

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
├── indexer/                # Custom Web3.py blockchain indexer
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
- **[Web3.py Documentation](https://web3py.readthedocs.io/)**: Python Ethereum library
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/)**: Database reference

## 🎯 Quick Reference

| Mode | Command | Time | Best For |
|------|---------|------|----------|
| **Demo** | `./run.sh mock` | 10s | UI testing, demos |
| **Development** | `./run.sh dev` | 60s | Full-stack development |
| **Production** | `./run.sh prod` | 5m | Real deployments |

**Stop any mode**: `Ctrl+C` (automatically cleans up all services)

---

**Built for the DeFi community** - Ready to monitor Dutch auctions across all major networks! 🚀