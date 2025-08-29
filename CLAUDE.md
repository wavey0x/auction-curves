# CLAUDE.md - LLM Development Guide for Auction System

## Project Overview

**Auction System** is a comprehensive monorepo implementing a Dutch auction monitoring system with multi-chain support. The system tracks blockchain auction events, provides real-time monitoring, and offers a modern React dashboard for visualizing auction activity.

### Core Architecture
- **Auction**: Smart contracts managing Dutch auctions for token swaps (renamed from "AuctionHouse")
- **AuctionRound**: Individual auction rounds created by each "kick" with incremental IDs  
- **AuctionSale**: Individual "takes" within rounds with sequence numbers

## Technology Stack

### Backend
- **API**: FastAPI with Python 3.9+ for RESTful endpoints
- **Database**: PostgreSQL with TimescaleDB for time-series data
- **Indexing**: Rindexer for blockchain event processing
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
- **Indexing**: Rindexer for dynamic contract discovery via factory pattern

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
├── indexer/rindexer/       # Blockchain event indexing
│   ├── rindexer-local.yaml # Development configuration (dynamic factory discovery)
│   └── rindexer-multi.yaml # Production multi-network configuration (5 chains)
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
DEV_DATABASE_URL=postgresql://postgres:password@localhost:5432/auction
DEV_NETWORKS_ENABLED=local
DEV_FACTORY_ADDRESS=0x335796f7A0F72368D1588839e38f163d90C92C80

# Mock mode variables (MOCK_*)  
MOCK_DATABASE_URL=           # Empty - no database needed
MOCK_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base,local

# Production mode variables (PROD_*)
PROD_DATABASE_URL=postgresql://user:pass@prod-host:5432/auction
PROD_NETWORKS_ENABLED=ethereum,polygon,arbitrum,optimism,base
PROD_ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
```

### Deployment Modes

#### Development Mode (`./run.sh dev`)
- Local Anvil blockchain (chain_id: 31337)
- PostgreSQL via Docker
- Smart contract auto-deployment
- Rindexer with local config
- Full API with database integration
- React dev server with hot reload
- Price monitoring and activity simulation

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
- Rindexer with multi-network config
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

### Multi-Chain Design
All tables include `chain_id` fields for multi-network support:

- **tokens**: Token metadata cache with chain_id
- **auction_parameters**: Contract parameters per chain
- **auction_rounds**: Round tracking with incremental round_id per auction
- **auction_sales**: Individual sales with sequence numbers per round  
- **price_history**: Time-series price data optimized with TimescaleDB

### Recent Schema Updates
- Renamed `auction_house` → `auction` (Migration 004)
- Renamed `auction_house_parameters` → `auction_parameters`
- Updated API query keys: `auctionHouseSales` → `auctionSales`

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

// ui/src/components/SalesTable.tsx  
- Fixed React key prop warnings
- Null safety for sale.sale_id fields
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
import { useQuery, useMutation } from '@tanstack/react-query'

// Query keys follow pattern: ['auctions', address, 'sales']
const { data, isLoading, error } = useQuery({
  queryKey: ['auctions', address],
  queryFn: () => apiClient.getAuction(address),
  refetchInterval: 30000  // 30-second polling
})
```

#### Component State
```typescript
// Local state with TypeScript interfaces
const [selectedView, setSelectedView] = useState<'auctions' | 'rounds' | 'takes'>('auctions')
const [filters, setFilters] = useState<AuctionFilters>({
  status: 'all',
  chain_id: undefined
})
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
- **Fixed**: React key prop warnings in SalesTable and Dashboard
- **Fixed**: TypeError with undefined sale.sale_id (added null safety)
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
- ✅ Mode-specific prefixes (DEV_*, MOCK_*, PROD_*)
- ✅ Automatic legacy variable mapping
- ✅ Removed: .env.development, .env.production, .env.mock

### Code Quality Improvements
- ✅ Fixed all React key prop warnings
- ✅ Added null safety for API responses  
- ✅ Improved TypeScript type coverage
- ✅ Better error handling and loading states

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