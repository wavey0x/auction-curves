# Quick Start Guide

**Simple guide to get the Auction System running in any mode with the new unified configuration.**

## 🚀 Super Quick Start (30 seconds)

**Just want to see the UI working right now?**

```bash
# One command - that's it!
./run.sh mock
```

Then open: **http://localhost:3000** 🎉

---

## 🎯 Choose Your Adventure

All modes now use a **single `.env` file** and one unified `./run.sh` script!

### 🎭 Mock Mode - Instant UI Demo
**Perfect for**: UI testing, demos, frontend development

```bash
./run.sh mock
```

✅ **What you get**: Working UI with realistic test data  
✅ **Time to start**: ~10 seconds  
✅ **Requirements**: None (just Node.js and Python)  
✅ **Networks**: All supported with mock data  

### 🔧 Development Mode - Full Local Stack  
**Perfect for**: Smart contract development, integration testing

```bash  
./run.sh dev
```

✅ **What you get**: Real blockchain + database + indexing  
✅ **Time to start**: ~60 seconds  
✅ **Requirements**: Docker, Brownie, Foundry, Rindexer  
✅ **Networks**: Local Anvil blockchain (chain ID 31337)  

### 🚀 Production Mode - Multi-Network Deployment
**Perfect for**: Production deployments, real mainnet integration

```bash
# Configure your production settings first!
./run.sh prod

# Server-only (no UI):
./run.sh prod --no-ui
```

✅ **What you get**: Multi-network indexing + production database  
✅ **Time to start**: ~2-5 minutes  
✅ **Requirements**: Production DB, RPC providers, deployed contracts  
✅ **Networks**: Ethereum, Polygon, Arbitrum, Optimism, Base  

---

## ⚡ One-File Configuration

**Everything is now controlled by a single `.env` file:**

```bash
# 🎯 Switch modes by changing one line:
APP_MODE=mock    # Mock mode
APP_MODE=dev     # Development mode  
APP_MODE=prod    # Production mode

# 🔧 Mode-specific configuration with prefixes:
DEV_DATABASE_URL=postgresql://postgres:password@localhost:5432/auction
MOCK_DATABASE_URL=    # Empty - no database needed
PROD_DATABASE_URL=postgresql://user:pass@prod-host:5432/auction

# 🌐 Network configuration per mode:
DEV_NETWORKS_ENABLED=local
MOCK_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base,local  
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base
```

**No more copying different .env files!** Just edit the `.env` file and run `./run.sh [mode]`.

---

## 🛠️ Quick Setup

### First Time Setup

1. **Clone and setup**:
   ```bash
   cd auction-system
   # The .env file should already exist with sensible defaults
   ```

2. **Pick your mode and run**:
   ```bash
   ./run.sh mock    # Start with mock mode
   ./run.sh dev     # or development mode
   ./run.sh prod    # or production mode
   ```

3. **Open the UI**: http://localhost:3000

### Switching Modes

**Option 1: Command override (temporary)**
```bash
./run.sh mock    # Use mock mode this time
./run.sh dev     # Use dev mode this time  
./run.sh prod    # Use prod mode this time
```

**Option 2: Edit .env file (persistent)**  
```bash
# Edit .env file:
APP_MODE=mock    # Will be used by default

# Then run without specifying mode:
./run.sh         # Uses APP_MODE from .env
```

---

## 📊 What You'll See

### Mock Mode Dashboard
- ✅ 6 different auction houses with realistic names
- ✅ Active rounds with time remaining and progress bars  
- ✅ Recent sales across multiple networks
- ✅ All networks showing with fake but realistic data
- ✅ Consistent, predictable test data

### Development Mode Dashboard
- ✅ Real smart contracts deployed on local Anvil
- ✅ Live price updates and activity simulation  
- ✅ Real database with actual blockchain events
- ✅ Rindexer indexing events in real-time
- ✅ Price monitoring and automated market activity

### Production Mode Dashboard  
- ✅ Real multi-network auction data
- ✅ Live indexing from Ethereum, Polygon, Arbitrum, etc.
- ✅ Production database with real transaction history
- ✅ Network health monitoring at `/networks`
- ✅ Real auction houses and their activity

---

## 🎛️ Advanced Configuration

### Production Setup Example

Edit your `.env` file for production:

```bash
# 1. Set mode
APP_MODE=prod

# 2. Configure database  
PROD_DATABASE_URL=postgresql://user:secure_password@prod-db.com:5432/auction

# 3. Enable networks you want
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum

# 4. Set RPC providers (replace YOUR_KEY)
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
PROD_POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/YOUR_KEY  
PROD_ARBITRUM_RPC_URL=https://arbitrum-mainnet.infura.io/v3/YOUR_KEY

# 5. Set your deployed factory contracts
PROD_ETHEREUM_FACTORY_ADDRESS=0x1234...YourEthereumFactory  
PROD_POLYGON_FACTORY_ADDRESS=0x5678...YourPolygonFactory
PROD_ARBITRUM_FACTORY_ADDRESS=0x9abc...YourArbitrumFactory

# 6. Set start blocks (when you deployed)
PROD_ETHEREUM_START_BLOCK=18500000
PROD_POLYGON_START_BLOCK=45000000  
PROD_ARBITRUM_START_BLOCK=100000000
```

Then run:
```bash
./run.sh prod
```

### Development Customization

Edit `.env` for custom development setup:
```bash
# Custom local database
DEV_DATABASE_URL=postgresql://myuser:mypass@localhost:5433/my_auction_db

# Custom factory address (after deployment)
DEV_FACTORY_ADDRESS=0xYourCustomFactoryAddress

# Custom start block
DEV_START_BLOCK=100
```

---

## 🔍 Monitoring & Health Checks

### Check System Status
```bash
# Health check (all modes)
curl http://localhost:8000/health

# Network status (dev/prod modes)  
curl http://localhost:8000/networks

# API documentation  
open http://localhost:8000/docs
```

### Development Mode Monitoring
```bash
# Check local blockchain
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:8545

# Check database
pg_isready -h localhost -p 5432

# Check Rindexer logs (it runs in background)
# Logs will show in the ./run.sh dev terminal
```

### Production Mode Monitoring
```bash
# Check all configured networks
curl http://localhost:8000/networks | jq

# Check specific network health
curl http://localhost:8000/networks/ethereum | jq
curl http://localhost:8000/networks/polygon | jq

# Monitor indexing progress
curl http://localhost:8000/auctions | jq '.[] | .last_indexed_block'
```

---

## 🆘 Troubleshooting

### Common Issues & Solutions

**"Port already in use"**
```bash  
# Find and kill processes using ports
lsof -i :3000 && kill -9 $(lsof -t -i :3000)  # UI
lsof -i :8000 && kill -9 $(lsof -t -i :8000)  # API
lsof -i :8545 && kill -9 $(lsof -t -i :8545)  # Anvil
```

**"Environment configuration failed"**
```bash
# Check .env file syntax
source .env && echo "✅ .env OK" || echo "❌ .env has syntax errors"

# Verify required variables are set  
./run.sh dev  # Will show what's loaded
```

**Mock Mode Issues** (very rare)
```bash
# Should just work - check basic requirements
node --version  # Need Node.js
python3 --version  # Need Python 3
```

**Development Mode Issues**
```bash
# Check Docker
docker --version && docker ps

# Start database manually if needed
docker-compose up -d postgres

# Check if database is ready
pg_isready -h localhost -p 5432

# Check if Brownie is installed
brownie --version

# Check if Anvil is available
anvil --version  
```

**Production Mode Issues**
```bash
# Test RPC connectivity
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  $PROD_ETHEREUM_RPC_URL

# Test database connectivity
psql $PROD_DATABASE_URL -c "SELECT 1;"

# Verify factory contract exists
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_getCode","params":["'$PROD_ETHEREUM_FACTORY_ADDRESS'","latest"],"id":1}' \
  $PROD_ETHEREUM_RPC_URL
```

### Get Help

**Check the full documentation:**
- `MODES.md` - Detailed mode information  
- `architecture.md` - Full system architecture
- API Docs: http://localhost:8000/docs (when running)

**Script Help:**
```bash
./run.sh --help    # Show all options
```

---

## 📈 Performance Tips

### Mock Mode (Fastest)
- Always use for UI development
- Great for CI/CD pipelines
- Perfect for demos and screenshots

### Development Mode (Balanced)  
- Use for smart contract testing
- Good for integration development
- Restart occasionally to reset blockchain state

### Production Mode (Robust)
- Monitor `/networks` endpoint for health  
- Use `--no-ui` flag for server deployments
- Set up database connection pooling for high load
- Consider multiple RPC providers for redundancy

---

## 🎯 Quick Reference

| Need | Command | Time | Access |
|------|---------|------|--------|
| **Quick Demo** | `./run.sh mock` | 10s | http://localhost:3000 |
| **Development** | `./run.sh dev` | 60s | http://localhost:3000 |
| **Production** | `./run.sh prod` | 5m | http://localhost:3000 |
| **Server Only** | `./run.sh prod --no-ui` | 3m | API only |
| **Help** | `./run.sh --help` | 0s | Terminal |

**Stop any mode**: `Ctrl+C` (cleans up all services automatically)

The new unified system makes it incredibly easy to switch between development, testing, and production environments with minimal configuration changes! 🚀