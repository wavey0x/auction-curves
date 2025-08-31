# CLAUDE.md - LLM Development Guide for Auction System

## Project Overview

**Auction System** is a comprehensive monorepo implementing a Dutch auction monitoring system with multi-chain support. The system tracks blockchain auction events, provides real-time monitoring, and offers a modern React dashboard for visualizing auction activity.

### Core Architecture

- **Auction**: Smart contracts managing Dutch auctions for token swaps (renamed from "AuctionHouse")
- **Round**: Individual auction rounds created by each "kick" with incremental IDs (renamed from "AuctionRound")
- **Take**: Individual "takes" within rounds with sequence numbers (renamed from "AuctionSale")

## Technology Stack

### Backend

- **API**: FastAPI with Python 3.9+ for RESTful endpoints
- **Database**: PostgreSQL with TimescaleDB for time-series data
- **Indexing**: Custom Web3.py indexer for blockchain event processing
- **Blockchain**: Smart contracts written in Solidity

### Frontend

- **Framework**: React 18.2+ with TypeScript 5.0+
- **Build Tool**: Vite 5.0+ with hot module replacement
- **State Management**: @tanstack/react-query for server state
- **Routing**: react-router-dom v6.8+
- **Styling**: TailwindCSS 3.3+ with custom design system
- **Icons**: lucide-react with 294+ icons
- **Animations**: framer-motion for micro-interactions

### Development Tools

- **Smart Contracts**: Brownie framework with Anvil local blockchain
- **Container**: Docker Compose for PostgreSQL
- **Code Quality**: ESLint, TypeScript strict mode
- **Package Manager**: npm with lock files
- **Indexing**: Custom Web3.py indexer with factory pattern discovery

## File Structure

```
/
├── contracts/core/          # Solidity smart contracts
│   ├── Auction.sol         # Main auction contract (renamed from AuctionHouse.sol)
│   ├── AuctionFactory.sol  # Factory for deploying auctions
│   └── libraries/          # Shared contract libraries
├── ui/                     # React frontend application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-based page components
│   │   ├── lib/            # API client and utilities
│   │   ├── types/          # TypeScript type definitions
│   │   └── main.tsx        # Application entry point
│   ├── package.json        # Dependencies and scripts
│   └── tailwind.config.js  # TailwindCSS configuration
├── monitoring/api/         # FastAPI backend
│   ├── app.py              # Production API server
│   ├── simple_server.py    # Mock API for development
│   └── requirements.txt    # Python dependencies
├── indexer/                # Custom Web3.py blockchain event indexer
│   ├── indexer.py          # Main indexer implementation
│   ├── requirements.txt    # Python dependencies
│   └── config.yaml         # Factory addresses and network configuration
├── data/postgres/          # Database schema and migrations
├── scripts/                # Deployment and utility scripts
├── .env                    # Unified environment configuration
└── run.sh                  # Unified deployment script
```

## Environment Configuration

### Unified Configuration System

**Environment Files Structure** (Simplified):

- `.env` - Actual configuration (copy from `.env.example`)
- `.env.example` - Template with all options and documentation

**Removed Files** (old system):

- ~~`.env.development`~~
- ~~`.env.production`~~
- ~~`.env.mock`~~

The system uses a single `.env` file with mode-specific prefixes:

```bash
APP_MODE=dev|mock|prod

# Development mode variables (DEV_*)
DEV_DATABASE_URL=postgresql://postgres@localhost:5432/auction_dev
DEV_NETWORKS_ENABLED=local
DEV_FACTORY_ADDRESS=0x335796f7A0F72368D1588839e38f163d90C92C80

# Mock mode variables (MOCK_*)
MOCK_DATABASE_URL=           # Empty - no database needed
MOCK_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base,local

# Production mode variables (PROD_*)
PROD_DATABASE_URL=postgresql://username:password@prod-db-host:5432/auction_prod
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
```

### Deployment Modes

#### Development Mode (`./run.sh dev`)

- Local Anvil blockchain (chain_id: 31337)
- PostgreSQL via Docker
- Smart contract auto-deployment
- **Custom Web3.py indexer** (see below)
- Full API with database integration
- React dev server with hot reload
- Price monitoring and activity simulation

**Dev Mode Custom Indexer:**
In development mode, the custom Web3.py indexer processes blockchain events:

- `./run.sh dev` deploys contracts and starts the indexer
- Factory pattern automatically discovers new auction deployments
- Real-time event processing with database integration
- Human-readable value conversion (9 instead of 9e18)
- Simplified schema with unified column names

**✅ IMPLEMENTED: Custom Web3.py Indexer Features**

- ✅ **Factory Discovery**: Automatic detection of ALL deployed auctions
- ✅ **Human-Readable Values**: Converts wei/RAY to readable decimals (e.g., 0.005 instead of 995000000000000000000000000)
- ✅ **Unified Schema**: Clean column names (version, decay_rate, update_interval)
- ✅ **Real-Time Processing**: Continuous event monitoring with 5-second polling
- ✅ **Multi-Version Support**: Handles both legacy (0.0.1) and modern (0.1.0) auction contracts
- ✅ **Database Integration**: Direct PostgreSQL insertion with proper error handling

**Custom Indexer Architecture:**

```python
# indexer/indexer.py - Main indexer implementation
# Factory pattern event discovery
factory_filter = contract.events.DeployedNewAuction.create_filter(
    fromBlock=start_block
)

# Process events with human-readable conversion
decay_rate = 1.0 - (float(step_decay_rate_wei) / 1e27)  # 0.005 instead of 995e24
starting_price = float(starting_price_wei) / 1e18      # 9.0 instead of 9e18
```

#### Mock Mode (`./run.sh mock`)

- Hardcoded test data (no blockchain/database required)
- Simple FastAPI server (`simple_server.py`)
- React dev server
- All networks supported with fake data
- 10-second startup time
- Perfect for UI development and testing

#### Production Mode (`./run.sh prod`)

- Multi-network blockchain indexing
- Production database
- Full API with all endpoints
- Custom Web3.py indexer with multi-network support
- Optional UI (use `--no-ui` flag for server-only)
- Health monitoring endpoints

## API Endpoints

### Core Auction Endpoints

```
GET  /auctions                           # List auctions with filtering
GET  /auctions/{address}                 # Individual auction details
GET  /auctions/{address}/rounds          # Round history
GET  /auctions/{address}/sales           # Sales data
GET  /auctions/{address}/price-history   # Price trends
```

### System Endpoints

```
GET  /health                            # Health check
GET  /docs                              # API documentation
GET  /chains                            # Supported blockchains
GET  /tokens                            # Token registry
GET  /system/stats                      # System statistics
```

## Database Schema

### Multi-Chain Design with Unified Tables

All tables include `chain_id` fields for multi-network support:

**Custom Business Logic Tables:**

- **tokens**: Token metadata cache with chain_id
- **auctions**: Contract parameters per chain (renamed from auction_parameters)
- **rounds**: Round tracking with incremental round_id per auction
- **takes**: Individual takes with sequence numbers per round
- **price_history**: Time-series price data optimized with TimescaleDB

**Custom Indexer Tables:**
The Web3.py indexer populates business logic tables directly:

- **auctions**: Contract parameters with human-readable values (version, decay_rate, update_interval)
- **rounds**: Round tracking with auto-incrementing round_id per auction
- **takes**: Individual takes with sequence numbers per round
- **tokens**: Token metadata cache automatically populated from discovered contracts

### Custom Indexer Benefits

- **Scalability**: Factory pattern discovers new auctions automatically
- **Human-Readable**: All values converted to decimals (decay_rate: 0.005 vs step_decay: 995000000000000000000000000)
- **Clean Schema**: Unified column names (version vs auction_version, update_interval vs update_interval_minutes)
- **Real-Time**: 5-second polling with immediate database updates
- **Error Resilient**: Comprehensive error handling and logging

### Recent Schema Updates

- **Migration 004**: Renamed `auction_house` → `auction` tables
- **Migration 006**: Schema cleanup for human-readable values
  - `auction_version` → `version`
  - `update_interval_minutes` → `update_interval` (now in seconds)
  - `decay_rate_percent` → `decay_rate` (now as decimal: 0.005 instead of 0.5%)
  - Consolidated `fixed_starting_price` + `starting_price` → `starting_price`
  - All values converted to human-readable format (9.0 instead of 9e18)
- **Migration 008**: Renamed tables and removed constraints
  - `auction_rounds` → `rounds`
  - `auction_sales` → `takes`
  - Removed all foreign key constraints for better reliability
  - Increased column sizes: VARCHAR(42) → VARCHAR(100) for addresses, VARCHAR(66) → VARCHAR(100) for tx hashes

### Database User Standards

**CRITICAL**: To prevent confusion and ensure consistent access patterns across services, the following database user standards MUST be followed:

#### User Account Rules

- **Development Environment**: ALWAYS use postgres user account for all database connections
  - Database: `auction_dev`
  - Connection: `postgresql://postgres@localhost:5432/auction_dev`
  - User MUST have SUPERUSER privileges in PostgreSQL container
- **Production Environment**: Use `postgres` user for administrative tasks, service-specific users for applications
  - Database: `auction_prod`
  - Connection: `postgresql://username:password@prod-host:5432/auction_prod`

#### Common Pitfalls to Avoid

- ❌ **DO NOT** use `postgres` user for development services - this creates confusion
- ❌ **DO NOT** mix database names (`auction` vs `auction_dev`)
- ❌ **DO NOT** assume user permissions - always grant explicit access when setting up
- ✅ **ALWAYS** verify the exact database user and name before connecting
- ✅ **ALWAYS** use environment-specific database names (`_dev`, `_prod` suffixes)

#### Container Setup Commands

```bash
# Create wavey user with proper privileges (run once)
docker exec auction_postgres psql -U postgres -c "CREATE USER wavey WITH SUPERUSER PASSWORD 'password';"

# Grant all privileges on development database
docker exec auction_postgres psql -U postgres -d auction_dev -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO wavey; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO wavey;"
```

#### Verification Steps

Always verify database connection settings:

```bash
# Test connection works
python3 -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres@localhost:5432/auction_dev'); print('✅ Connection successful')"

# Verify table access
docker exec auction_postgres psql -U wavey -d auction_dev -c "SELECT COUNT(*) FROM auctions;"
```

## Frontend Architecture

### Design System

#### Color Palette (TailwindCSS Custom Colors)

```javascript
colors: {
  gray: {
    800: '#1e293b',    // Dark backgrounds
    850: '#1a202c',    // Darker elements
    900: '#0f172a',    // Primary background
    950: '#020617',    // Deepest black
  },
  primary: {
    400: '#60a5fa',    // Active states
    500: '#3b82f6',    // Primary brand
    600: '#2563eb',    // Hover states
    700: '#1d4ed8',    // Selected states (darker for better contrast)
  }
}
```

#### Typography

- **Primary Font**: Inter (system-ui fallback)
- **Monospace**: JetBrains Mono, Fira Code
- **Sizes**: Tailwind's default scale with custom text-gradient utility

#### Component Patterns

- **Dark Theme**: Default and primary theme using gray-900/950 backgrounds
- **Glassmorphism**: Backdrop blur with semi-transparent backgrounds
- **Micro-animations**: Framer-motion for hover states and transitions
- **Responsive Design**: Mobile-first with lg: breakpoints
- **Component Composition**: Small, reusable components with TypeScript interfaces

### Key UI Components

#### Layout & Navigation

```typescript
// ui/src/components/Layout.tsx
- Sticky header with backdrop blur
- Live status indicators
- Responsive navigation
- Fixed footer with system status
```

#### Data Display

```typescript
// ui/src/components/AuctionsTable.tsx
- Sortable columns with chain icons
- Round display format: "R{id}" (updated from "#{id}")
- Real-time data updates via React Query
- Multi-chain filtering

// ui/src/components/TakesTable.tsx
- Fixed React key prop warnings
- Null safety for take.sale_id fields
- Formatted timestamps and amounts
- Transaction hash links per chain
```

#### Interactive Elements

```typescript
// ui/src/pages/Dashboard.tsx
- Button groups with darker selected states (bg-primary-700)
- Subtle vertical separators between buttons
- Real-time data polling every 30 seconds
- Loading states and error handling
```

#### Data Visualization

```typescript
// ui/src/components/StackedProgressMeter.tsx
- Dual progress bars (time and volume)
- Color-coded progress states
- Responsive sizing with percentages
```

### State Management Patterns

#### API Data Fetching

```typescript
// ui/src/lib/api.ts
import { useQuery, useMutation } from "@tanstack/react-query";

// Query keys follow pattern: ['auctions', address, 'sales']
const { data, isLoading, error } = useQuery({
  queryKey: ["auctions", address],
  queryFn: () => apiClient.getAuction(address),
  refetchInterval: 30000, // 30-second polling
});
```

#### Component State

```typescript
// Local state with TypeScript interfaces
const [selectedView, setSelectedView] = useState<
  "auctions" | "rounds" | "takes"
>("auctions");
const [filters, setFilters] = useState<AuctionFilters>({
  status: "all",
  chain_id: undefined,
});
```

### Routing Structure

```typescript
// ui/src/App.tsx - Updated routes (removed "auction-house" terminology)
/                                    → Dashboard
/auction/:address                    → AuctionDetails
/round/:auctionAddress/:roundId      → RoundDetails
```

## Smart Contract Architecture

### Core Contracts

```solidity
// contracts/core/Auction.sol (renamed from AuctionHouse.sol)
contract Auction {
    // Dutch auction implementation
    // Configurable decay parameters
    // Round and sale tracking
}

// contracts/core/AuctionFactory.sol
contract AuctionFactory {
    // Deploys new Auction instances
    // Manages registry of deployed auctions
}
```

### Key Events

```solidity
event DeployedNewAuction(address indexed auction, address indexed deployer);
event AuctionRoundKicked(address indexed auction, uint256 indexed roundId, uint256 initialAvailable);
event AuctionSale(address indexed auction, uint256 indexed roundId, uint256 saleSeq, address indexed taker);
```

## Development Workflow

### Starting Development

```bash
# Quick UI testing (10 seconds)
./run.sh mock

# Full development stack (60 seconds)
./run.sh dev

# Production deployment (2-5 minutes)
./run.sh prod
```

### Common Development Tasks

#### Adding New UI Components

1. Create component in `ui/src/components/`
2. Add TypeScript interface for props
3. Use TailwindCSS classes following existing patterns
4. Export from component and add to relevant page
5. Test in all three deployment modes

#### Updating Database Schema

1. Create migration in `data/postgres/migrations/`
2. Update TypeScript types in `ui/src/types/auction.ts`
3. Update API endpoints in `monitoring/api/`
4. Test with development mode first

#### Adding New API Endpoints

1. Add endpoint to `monitoring/api/app.py` (production)
2. Add mock data to `monitoring/api/simple_server.py`
3. Update `ui/src/lib/api.ts` with new method
4. Add TypeScript types if needed
5. Test with both real and mock APIs

### Code Quality Standards

#### Variable Naming Rules

- Use concise, clear names without unnecessary verbosity
- Avoid redundant qualifiers like "normalized", "checksummed" in variable names
- Let context imply meaning (e.g., `address` in auction context implies auction address)
- Use snake_case for database columns, camelCase for TypeScript/JavaScript
- Prefer `version` over `auction_version`, `decay_rate` over `decay_rate_percent`

#### Address Handling

- Always store Ethereum addresses in checksummed format (EIP-55)
- Use case-insensitive database queries: `LOWER(address) = LOWER(%s)`
- Normalize addresses in indexer and API before database operations
- Frontend receives checksummed addresses from API

#### TypeScript

- Strict mode enabled in `tsconfig.json`
- Explicit return types for functions
- Interface definitions for all data structures
- No `any` types except for temporary development

#### React Patterns

- Functional components with hooks
- Props interfaces for all components
- Proper key props for list items (fixed recent warnings)
- Error boundaries for data fetching
- Loading states for async operations

#### Styling Guidelines

- Use TailwindCSS utility classes
- Follow mobile-first responsive design
- Use design system colors and spacing
- Add hover/focus states for interactive elements
- Test dark theme compatibility

## Testing Strategy

### Mock Mode Testing

- UI components with hardcoded data
- API endpoint structure validation
- Responsive design verification
- Cross-browser compatibility

### Development Mode Testing

- Real blockchain interaction testing
- Database integration verification
- Event indexing validation
- End-to-end user flows

### Production Testing

- Multi-network deployment verification
- Performance under load
- Database backup and recovery
- Security audit of API endpoints

## Troubleshooting Common Issues

### Port Conflicts

```bash
# Check what's using ports
lsof -i :3000  # React UI
lsof -i :8000  # API server
lsof -i :8545  # Anvil blockchain

# Kill processes
kill -9 <PID>
```

### React Errors Fixed

- **Fixed**: React key prop warnings in TakesTable and Dashboard
- **Fixed**: TypeError with undefined take.sale_id (added null safety)
- **Fixed**: Syntax errors from extra closing tags
- **Fixed**: Undefined variable references (auctionHouseDetails → auctionDetails)

### API Issues

- **Fixed**: NameError in simple_server.py (auction → auction_address)
- **Removed**: WebSocket functionality (replaced with polling)
- **Updated**: Endpoint names (auction-house → auction)

### Build Issues

```bash
# Clear caches
rm -rf ui/node_modules ui/dist
cd ui && npm install

# TypeScript issues
npm run lint
```

## Recent Major Updates

### Naming Consistency (2024)

- ✅ All "AuctionHouse" references updated to "Auction"
- ✅ Routes updated: `/auction-house/` → `/auction/`
- ✅ Database tables renamed with Migration 004
- ✅ Component files renamed and consolidated
- ✅ Variable names updated throughout codebase

### Configuration Simplification

- ✅ Multiple .env files → Single unified .env file + .env.example template
- ✅ Multiple run scripts → Single parameterized run.sh
- ✅ Mode-specific prefixes (DEV*\*, MOCK*\_, PROD\_\_)
- ✅ Automatic legacy variable mapping
- ✅ Removed: .env.development, .env.production, .env.mock

### Custom Web3.py Indexer Implementation (Latest)

- ✅ **Factory Discovery**: Automatic detection of ALL deployed auctions
- ✅ **Human-Readable Values**: All wei/RAY values converted to decimals
- ✅ **Clean Schema**: Unified column names (version, decay_rate, update_interval)
- ✅ **Real-Time Processing**: 5-second blockchain polling with immediate database updates
- ✅ **Multi-Version Support**: Handles legacy (0.0.1) and modern (0.1.0) auction contracts
- ✅ **Error Resilience**: Comprehensive error handling and transaction rollback
- ✅ **Clean Architecture**: Eliminated 10+ individual contract entries
- ✅ **Template Simplification**: Removed complex individual auction generation logic

### Database Refactoring (August 2025)

- ✅ **Table Renaming**: `auction_rounds` → `rounds`, `auction_sales` → `takes`
- ✅ **Constraint Removal**: All foreign key constraints removed for development flexibility
- ✅ **Column Size Increases**: Address fields (42→100), tx hashes (66→100), sale_id (100→200)
- ✅ **Database User Standards**: Enforced `wavey` user for dev, standardized connection patterns
- ✅ **Schema Migration**: Clean migration 008 with validation and rollback safety
- ✅ **API Model Updates**: `AuctionSale` → `Take` with backward compatibility aliases

### Indexer System Improvements (August 2025)

- ✅ **ABI Loading Fix**: Resolved critical Brownie artifact vs clean ABI array format issues
- ✅ **Column Reference Fix**: Corrected `auction_version` → `version` database column mismatch
- ✅ **Database Connection**: Fixed user permissions and connection string issues
- ✅ **Configuration Updates**: Dynamic factory addresses from deployment rather than hardcoded
- ✅ **Clean ABI Extraction**: Automated extraction of clean ABIs from Brownie build artifacts
- ✅ **Error Handling**: Comprehensive error handling with proper database rollback

### Code Quality Improvements

- ✅ Fixed all React key prop warnings
- ✅ Added null safety for API responses
- ✅ Improved TypeScript type coverage
- ✅ Better error handling and loading states
- ✅ Eliminated YAML parsing errors with proper factory configuration
- ✅ **Database Provider Implementation**: Real SQL queries replacing mock implementations

## Performance Considerations

### Frontend Optimization

- React Query for efficient data fetching and caching
- Component memoization for expensive renders
- Lazy loading for route-based code splitting
- Optimized bundle size with Vite

### Backend Optimization

- TimescaleDB for time-series data performance
- Database indexes for common query patterns
- API response pagination for large datasets
- Connection pooling for high load scenarios

### Development Speed

- Mock mode for instant UI feedback (10s startup)
- Hot module replacement with Vite
- TypeScript for early error detection
- Unified scripts for consistent environments

## Documentation Links

### Official Documentation

- **Rindexer Factory Pattern**: https://rindexer.xyz/docs/start-building/yaml-config/contracts#factory
- **Rindexer Configuration**: https://rindexer.xyz/docs/start-building/yaml-config
- **TimescaleDB**: https://docs.timescale.com/
- **FastAPI**: https://fastapi.tiangolo.com/

This system provides a robust foundation for monitoring Dutch auction activity across multiple blockchain networks with a modern, responsive user interface and efficient backend architecture.

- please update @CLAUDE.md as necessary to account for our refactoring. also make a note about the account used for databases - i notice its easy for llm to get confused between `postgres` and the local account user (`wavey`) on which to login with. we should enforce a rule for which account our services use, etc.
