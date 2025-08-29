# Auction System Operating Modes

The Auction System supports three distinct operating modes, all managed through a **single unified `.env` file** and the simplified `./run.sh` script.

## 🎭 Mock Mode

**Purpose**: Pure UI testing with hardcoded data - no blockchain or database required

**When to use**:
- UI/frontend development and testing
- Quick demos and prototypes  
- CI/CD pipeline testing
- When you just want to see the interface working

**Setup**:
```bash
# Single command - that's it!
./run.sh mock
```

**Features**:
- ✅ Hardcoded test data matching real API structure
- ✅ Fast startup (< 10 seconds)
- ✅ No external dependencies (no blockchain/database)
- ✅ Perfect for frontend developers
- ✅ Consistent, predictable data for testing
- ✅ All networks supported with mock data

**Access**:
- UI: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 🔧 Development Mode  

**Purpose**: Full local development with Anvil blockchain and PostgreSQL

**When to use**:
- Smart contract development and testing
- Full-stack feature development  
- Integration testing with real blockchain simulation
- Local development that closely mimics production

**Setup**:
```bash
# Full development stack with one command
./run.sh dev
```

**Prerequisites** (automatically checked):
- Docker (for PostgreSQL)
- Brownie framework: `pip install eth-brownie`  
- Foundry (for Anvil): [Install guide](https://book.getfoundry.sh/getting-started/installation)
- Rindexer: [Install guide](https://rindexer.xyz)

**Features**:
- ✅ Real local blockchain (Anvil) 
- ✅ Real PostgreSQL database with full schema
- ✅ Smart contract deployment and interaction
- ✅ Event indexing with Rindexer (local config)
- ✅ Price monitoring and activity simulation
- ✅ Full API functionality with real data

**Access**:
- UI: http://localhost:3000
- API Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health
- Anvil RPC: http://localhost:8545

---

## 🚀 Production Mode

**Purpose**: Production deployment with real blockchain networks

**When to use**:
- Production deployments on mainnet
- Staging environments  
- Real multi-network blockchain integration
- Production-scale testing

**Setup**:
```bash
# Configure production values in .env first, then:
./run.sh prod

# Optional: Skip UI for server-only deployment
./run.sh prod --no-ui
```

**Configuration Required**:
Edit the `PROD_*` variables in your `.env` file:
```bash
# Enable networks you want to index
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base

# Network RPC URLs (replace with your provider keys)
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_key
PROD_POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/your_key
# ... etc

# Factory contract addresses (your deployed contracts)
PROD_ETHEREUM_FACTORY_ADDRESS=0x_YOUR_ETHEREUM_FACTORY
PROD_POLYGON_FACTORY_ADDRESS=0x_YOUR_POLYGON_FACTORY  
# ... etc
```

**Features**:
- ✅ Multi-network support (Ethereum, Polygon, Arbitrum, Optimism, Base)
- ✅ Production database with high availability
- ✅ Real blockchain indexing across all networks
- ✅ Multi-network Rindexer configuration  
- ✅ Production security and performance optimizations

**Access**:
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health  
- Networks: http://localhost:8000/networks

---

## 📁 Unified Configuration

### Single `.env` File Structure

All modes now use **one unified `.env` file** with mode-specific prefixes:

```bash
# Core settings
APP_MODE=dev                    # Controls which mode settings are used

# Mode-specific database URLs
DEV_DATABASE_URL=postgresql://postgres:password@localhost:5432/auction
MOCK_DATABASE_URL=              # Empty - mock mode uses no database
PROD_DATABASE_URL=postgresql://user:pass@prod-host:5432/auction

# Mode-specific network configuration  
DEV_NETWORKS_ENABLED=local
MOCK_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base,local
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base

# Mode-specific RPC URLs (production example)
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your_key
PROD_POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/your_key
# ... etc
```

### Environment Variable Prefixes

| Prefix | Mode | Description |
|--------|------|-------------|
| `DEV_*` | Development | Local Anvil + PostgreSQL configuration |
| `MOCK_*` | Mock | Mock data configuration (minimal) |
| `PROD_*` | Production | Real blockchain network configuration |

### Legacy Compatibility

The system automatically sets legacy environment variables based on your `APP_MODE`:
- `DATABASE_URL` → Set from `DEV_DATABASE_URL`, `MOCK_DATABASE_URL`, or `PROD_DATABASE_URL`  
- `NETWORKS_ENABLED` → Set from appropriate mode prefix
- `FACTORY_ADDRESS` → Set from mode-specific factory address
- etc.

---

## 🔄 Quick Mode Switching

**Change modes instantly by editing one line in `.env`:**

```bash
# Switch to development mode
APP_MODE=dev
./run.sh dev

# Switch to mock mode  
APP_MODE=mock
./run.sh mock

# Switch to production mode
APP_MODE=prod  
./run.sh prod
```

**Or override via command line:**
```bash
# Temporarily use mock mode regardless of .env setting
./run.sh mock

# The script parameter always overrides the .env APP_MODE
```

---

## 🎯 Mode Comparison

| Feature | Mock Mode | Development Mode | Production Mode |
|---------|-----------|------------------|-----------------|
| **Startup Time** | ~10 seconds | ~60 seconds | ~2-5 minutes |
| **Data Source** | Hardcoded mock | Local blockchain | Real blockchain |
| **Database** | ❌ None | ✅ Local PostgreSQL | ✅ Production DB |
| **Blockchain** | ❌ None | ✅ Anvil (local) | ✅ Multiple networks |
| **Indexing** | ❌ None | ✅ Rindexer local | ✅ Rindexer multi-net |
| **Networks** | ✅ All (fake data) | ✅ Local (31337) | ✅ Mainnet/L2s |
| **API Endpoints** | `/` prefix | `/` prefix | `/` prefix |
| **Contract Deploy** | ❌ Not needed | ✅ Automated | ❌ Manual |
| **RPC Calls** | ❌ Mocked | ✅ localhost:8545 | ✅ Infura/Alchemy |

---

## 🆘 Troubleshooting

### Environment Issues
```bash
# Check your current configuration
./run.sh dev    # Will show loaded environment variables

# Validate .env file syntax
source .env && echo "✅ .env syntax OK"
```

### Port Conflicts  
```bash
# Find what's using ports
lsof -i :3000   # React UI
lsof -i :8000   # API server  
lsof -i :8545   # Anvil blockchain (dev mode)

# Kill conflicting processes
kill -9 <PID>
```

### Mode-Specific Issues

**Mock Mode**:
- No external dependencies required
- Should always work if ports are available

**Development Mode**:  
- Ensure Docker is running: `docker --version && docker ps`
- Check PostgreSQL: `pg_isready -h localhost -p 5432`
- Verify Anvil: `curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545`

**Production Mode**:
- Validate RPC URLs: `curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' $PROD_ETHEREUM_RPC_URL`
- Check database connectivity: `psql $PROD_DATABASE_URL -c "SELECT 1;"`
- Verify factory addresses are valid contract addresses

---

## 💡 Best Practices

### For Development
1. **Start with Mock Mode** - Get familiar with the UI quickly
2. **Use Dev Mode for Integration** - Test real blockchain interactions
3. **Keep .env Updated** - Always commit your .env changes (with secrets removed)

### For Production  
1. **Test in Staging First** - Use prod mode with testnet networks
2. **Monitor Network Health** - Check `/networks` endpoint regularly
3. **Use Environment Secrets** - Don't commit production RPC keys
4. **Database Backups** - Set up regular backups for production DB

### Configuration Management
```bash
# Copy .env as template for others
cp .env .env.example
# Remove sensitive values from .env.example before committing

# Use environment variable overrides for sensitive production data
export PROD_ETHEREUM_RPC_URL="$MAINNET_RPC_SECRET"
./run.sh prod
```

---

## 🔧 Architecture Benefits

1. **Single Source of Truth**: One `.env` file for all modes
2. **Zero Config Switching**: Change one variable to switch modes  
3. **Development Efficiency**: Mock mode for fast UI iteration
4. **Production Ready**: Full multi-network support
5. **Consistent APIs**: Same interface across all modes
6. **Clear Separation**: Mode-specific prefixes prevent configuration conflicts

The unified configuration system makes it easy to develop locally, test with mock data, and deploy to production - all with the same codebase and minimal configuration changes.