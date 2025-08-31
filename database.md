# Database Access Guide

This guide explains how to set up and access the PostgreSQL database used by the Auction System monitoring platform.

## Overview

The Auction System uses a **single PostgreSQL database** with **TimescaleDB extension** for all components:

- **API Server**: FastAPI backend for web interface
- **Custom Web3.py Indexer**: Blockchain event indexer with factory pattern discovery
- **Frontend**: React application (via API)
- **Analytics Scripts**: Price monitoring and data analysis

## Database Setup Options

### Option 1: Docker (Recommended)

Docker provides the easiest setup with automatic database initialization.

#### Prerequisites

- Docker and Docker Compose installed
- No PostgreSQL installation required

#### Quick Start

```bash
# 1. Start database service
docker-compose up postgres

# 2. Database will be automatically created with:
#    - Database: auction
#    - User: postgres
#    - Password: password
#    - Port: 5432 (mapped to host)
#    - TimescaleDB extension enabled
#    - Schema automatically applied from data/postgres/schema.sql
```

#### Connection Details (Docker)

```bash
# From host machine
DATABASE_URL="postgresql://postgres:password@localhost:5433/auction_dev"

# From other Docker containers
DATEABASE_URL="postgresql://postgres:password@postgres:5433/auction_dev"
```

### Option 2: Local PostgreSQL Installation

If you prefer to use a local PostgreSQL installation instead of Docker.

#### Prerequisites

```bash
# macOS with Homebrew
brew install postgresql timescaledb

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
# Follow TimescaleDB installation: https://docs.timescale.com/install/latest/self-hosted/installation-linux/

# Start PostgreSQL service
brew services start postgresql  # macOS
sudo systemctl start postgresql # Linux
```

#### Manual Database Setup

```bash
# 1. Create database and user
createdb auction
psql auction -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# 2. Apply schema
psql auction < data/postgres/schema.sql

# 3. Optional: Apply analytics schema
psql auction < data/postgres/analytics_schema.sql
```

#### Connection Details (Local)

```bash
# Default local connection (adjust as needed)
DATABASE_URL="postgresql://postgres@localhost:5432/auction"
# Or with password:
DATABASE_URL="postgresql://postgres:yourpassword@localhost:5432/auction"
```

## Environment Configuration

### 1. Create Environment File

```bash
# Copy example configuration
cp .env.example .env

# Edit with your database details
vim .env  # or your preferred editor
```

### 2. Environment Variables

```bash
# Main database connection (used by API, scripts)
DATABASE_URL=postgresql://postgres:password@localhost:5433/auction_dev

# Custom indexer database connection (usually the same)
INDEXER_DATABASE_URL=postgresql://postgres:password@localhost:5433/auction_dev

# Optional: Separate read-only connection for analytics
READONLY_DATABASE_URL=postgresql://postgres:password@localhost:5433/auction_dev
```

## Accessing the Database

### Method 1: Command Line (psql)

```bash
# Using environment variable
psql $DATABASE_URL

# Or directly
psql -h localhost -p 5432 -U postgres -d auction_house

# Common commands once connected:
\dt                    # List tables
\d auction_sales       # Describe table structure
\q                     # Quit
```

### Method 2: GUI Tools

**Recommended GUI clients:**

- **pgAdmin** (Web-based): `https://www.pgadmin.org/`
- **DBeaver** (Cross-platform): `https://dbeaver.io/`
- **TablePlus** (macOS/Windows): `https://tableplus.com/`
- **Postico** (macOS): `https://eggerapps.at/postico/`

**Connection settings for GUI tools:**

- Host: `localhost`
- Port: `5433`
- Database: `auction_dev`
- Username: `postgres`
- Password: `password` (or your custom password)

### Method 3: Application Connections

#### Python (FastAPI/Scripts)

```python
import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")
conn = await asyncpg.connect(DATABASE_URL)
```

#### Node.js (if needed)

```javascript
const { Pool } = require("pg");
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});
```

## Database Schema Overview

### Core Tables

#### Primary Tables (Application Data)

- **`auctions`**: Contract parameters and metadata with unix timestamps
- **`rounds`**: Individual auction rounds (hypertable) with kick timestamps
- **`takes`**: Sales within rounds (hypertable) with transaction timestamps
- **`tokens`**: Token metadata cache with discovery timestamps
- **`price_history`**: Price data over time (hypertable) with unix timestamps
- **`indexer_state`**: Per-factory indexer progress tracking

#### Custom Web3.py Indexer Features

The custom indexer provides:

- **Factory Pattern Discovery**: Automatically finds all deployed auctions
- **Human-Readable Values**: Converts wei/RAY to decimal format
- **Per-Factory State Tracking**: Independent progress per factory per network
- **Unix Timestamp Storage**: All events include both timestamptz and unix timestamp
- **Multi-Version Support**: Handles legacy (0.0.1) and modern (0.1.0) contracts

### Key Views

- **`active_auction_rounds`**: Currently active rounds with calculated data
- **`recent_takes`**: Recent takes with token metadata and unix timestamps

### TimescaleDB Features

- **Hypertables**: Time-series optimization for `rounds`, `takes`, `price_history`
- **Automatic partitioning**: By time for efficient queries
- **Continuous aggregates**: Available for analytics (optional)

## Common Database Operations

### Monitoring Data

```sql
-- Check recent activity
SELECT * FROM recent_takes LIMIT 10;

-- Active rounds
SELECT * FROM active_auction_rounds;

-- Database size
SELECT pg_size_pretty(pg_database_size('auction_house'));

-- Table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Data Analysis

```sql
-- Sales volume by day
SELECT
  DATE_TRUNC('day', timestamp) as day,
  COUNT(*) as takes,
  SUM(amount_taken::numeric) as volume
FROM takes
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY day
ORDER BY day;

-- Top auctions by activity
SELECT
  auction_address,
  COUNT(*) as total_takes,
  MAX(timestamp) as last_take
FROM takes
GROUP BY auction_address
ORDER BY total_takes DESC
LIMIT 10;

-- Unix timestamp analysis
SELECT 
  auction_address,
  to_timestamp(unix_timestamp) as event_time,
  unix_timestamp
FROM takes 
ORDER BY unix_timestamp DESC 
LIMIT 10;
```

## Troubleshooting

### Connection Issues

**"Connection refused"**

```bash
# Check if PostgreSQL is running
docker-compose ps postgres  # Docker
brew services list | grep postgresql  # macOS local

# Check port is available
lsof -i :5432
```

**"Database does not exist"**

```bash
# With Docker - recreate with schema
docker-compose down
docker-compose up postgres

# Local installation
createdb auction_house
psql auction_house < data/postgres/schema.sql
```

**"Permission denied"**

```bash
# Check user permissions
psql postgres -c "ALTER USER postgres CREATEDB;"
```

### Performance Issues

**Slow queries on time-series data**

```sql
-- Check hypertable status
SELECT * FROM timescaledb_information.hypertables;

-- Manually create hypertables if needed
SELECT create_hypertable('takes', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('rounds', 'kicked_at', if_not_exists => TRUE);
```

**Database growing too large**

```sql
-- Set up data retention (optional)
SELECT add_retention_policy('takes', INTERVAL '90 days');
SELECT add_retention_policy('price_history', INTERVAL '30 days');
SELECT add_retention_policy('rounds', INTERVAL '180 days');
```

## Backup and Restore

### Backup

```bash
# Full database backup
pg_dump $DATABASE_URL > auction_house_backup.sql

# Schema only
pg_dump --schema-only $DATABASE_URL > schema_backup.sql

# Data only
pg_dump --data-only $DATABASE_URL > data_backup.sql
```

### Restore

```bash
# Full restore
psql $DATABASE_URL < auction_house_backup.sql

# Or create fresh database and restore
createdb auction_house_restored
psql auction_house_restored < auction_house_backup.sql
```

## Multi-Chain Database Considerations

The schema is designed for **multi-chain support**:

- All tables include `chain_id` columns
- Foreign keys respect chain boundaries
- Indexes are optimized for chain-specific queries
- Single database handles multiple networks efficiently

For **high-scale production**, consider:

- **Read replicas** for analytics workloads
- **Connection pooling** (PgBouncer)
- **Separate databases per chain** if data volume is massive
- **Monitoring** with tools like pg_stat_statements

## Security Notes

### Production Deployment

- Change default passwords
- Use SSL connections (`sslmode=require`)
- Restrict network access
- Regular security updates
- Monitor connection logs

### Environment Variables

```bash
# Production example
DATABASE_URL="postgresql://auctions_user:secure_password@db.example.com:5433/auction_dev?sslmode=require"
```

## Development vs Production

### Development (Current Setup)

- Single PostgreSQL instance
- Docker Compose for easy setup
- All components use same database
- Local filesystem storage

### Production Considerations

- **Managed database service** (AWS RDS, Google Cloud SQL)
- **Connection pooling** (PgBouncer, built-in pooling)
- **Read replicas** for analytics and reporting
- **Automated backups** and point-in-time recovery
- **Monitoring and alerting** (pg_stat_statements, CloudWatch, etc.)
- **SSL/TLS encryption** in transit and at rest

## Next Steps

1. **Start with Docker** for development: `docker-compose up postgres`
2. **Connect with psql**: `psql $DATABASE_URL`
3. **Explore the schema**: `\dt` to list tables, `\d table_name` for structure
4. **Run the API**: Ensure `DATABASE_URL` environment variable is set
5. **Set up Custom Indexer**: Configure Web3.py indexer with per-factory tracking
6. **Monitor data flow**: Watch tables populate as events are indexed

For production deployment, refer to `architecture.md` for comprehensive setup instructions.
