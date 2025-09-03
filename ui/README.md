# Auction Analytics UI

Modern React dashboard for monitoring Dutch auction activity with real-time updates and dark theme aesthetics.

## Features

- **Real-time Monitoring**: WebSocket connections for live auction price updates
- **Dark Theme**: Modern, responsive interface optimized for extended use
- **Transaction Tables**: Comprehensive kick and take event displays with transaction links
- **Auction Details**: In-depth views with configuration, progress, and activity history
- **Token Management**: Support for multiple token types and symbols
- **Chain Integration**: Ethereum mainnet and Anvil local development support

## Architecture

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **State Management**: React Query for server state
- **Routing**: React Router v6
- **Real-time**: WebSocket connections for live data
- **Backend**: FastAPI REST API with PostgreSQL
- **Charts**: Recharts for data visualization

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Environment Setup

The UI expects the FastAPI backend to be running on `http://localhost:8000`. WebSocket connections use the same host.

## Component Structure

```
src/
├── components/          # Reusable UI components
│   ├── ActivityTable.tsx    # Transaction event tables
│   ├── AuctionCard.tsx      # Auction summary cards
│   ├── Layout.tsx           # App layout and navigation
│   ├── LoadingSpinner.tsx   # Loading states
│   └── StatsCard.tsx        # Metric display cards
├── pages/               # Main application pages
│   ├── Dashboard.tsx        # Main dashboard with overview
│   └── AuctionDetails.tsx   # Individual auction details
├── lib/                 # Utilities and API client
│   ├── api.ts              # API client and WebSocket
│   └── utils.ts            # Formatting and helper functions
└── types/               # TypeScript definitions
    └── auction.ts          # Auction-related types
```

## Key Features

### Dashboard
- System-wide statistics and metrics
- Active auction grid with real-time status
- Kick and take event tables with transaction links
- Chain logos and explorer integration

### Auction Details  
- Real-time price updates via WebSocket
- Auction progress visualization
- Token configuration display
- Complete activity history
- Enabled tokens listing

### Data Display
- Smart number formatting (K, M suffixes)
- Time-ago formatting with full timestamps
- Address truncation with copy functionality
- USD value estimates for token amounts
- Transaction links to block explorers

## Customization

The UI uses Tailwind CSS with a custom dark theme. Key customizations:

- Extended color palette for auction states
- Custom animations and transitions
- Glassmorphism effects for modern aesthetics  
- Responsive grid layouts
- Custom scrollbar styling

## WebSocket Integration

Real-time updates are handled through WebSocket connections:

```typescript
// Automatic reconnection on connection loss
// Live price updates for active auctions  
// Event notifications for kicks and takes
// Connection status indicators
```

## Development

```bash
# Start with hot reload
npm run dev

# Type checking
npx tsc --noEmit

# Lint code
npm run lint
```

## Integration

This UI is designed to work with:
- FastAPI backend (`/monitoring/api/`)
- Rindexer event indexing
- PostgreSQL with auction event tables
- Brownie smart contract deployment scripts
