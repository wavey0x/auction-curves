# Auction System Database Specification

**Version**: 1.0  
**Last Updated**: 2025-08-31  
**Status**: AUTHORITATIVE MASTER SPECIFICATION

This document serves as the **authoritative specification** for all database tables, columns, views, and naming conventions in the Auction System. All code changes must reference and conform to this specification.

## Table of Contents

- [Naming Conventions](#naming-conventions)
- [Core Tables](#core-tables)
- [Views](#views)
- [Indexes](#indexes)
- [Data Types](#data-types)
- [Change Management](#change-management)

## Naming Conventions

### Column Names (REQUIRED)

Always use **CONCISE NAMES** for consistency across all tables, views, and code:

| Concept | STANDARD NAME | Deprecated Names |
|---------|---------------|------------------|
| Version | `version` | `auction_version` |
| Decay Rate | `decay_rate` | `decay_rate_percent` |  
| Update Interval | `update_interval` | `price_update_interval`, `update_interval_minutes` |

**General Rules:**
- Use clear, concise names without unnecessary prefixes
- Avoid verbose qualifiers like "normalized", "checksummed" in column names
- Use context to imply meaning (e.g., `address` in auctions table implies auction address)

### Table Names

- Use singular form: `auction` not `auctions`
- Use short, descriptive names: `rounds`, `takes`
- Avoid prefixes like `auction_` when context is clear

### Constraints

- Primary keys: `{table_name}_pkey`
- Foreign keys: `fk_{table}_{referenced_table}`
- Indexes: `idx_{table}_{column(s)}`

### Address Handling

- All Ethereum addresses stored in checksummed format (EIP-55)
- Database queries use case-insensitive comparisons: `LOWER(address) = LOWER(%s)`
- Indexer normalizes addresses before database insertion
- API endpoints normalize incoming addresses automatically

## Core Tables

### `auctions`

**Purpose**: Master table for auction contracts across all chains

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `auction_address` | VARCHAR(100) | NOT NULL, PK | Contract address |
| `chain_id` | INTEGER | NOT NULL, PK, DEFAULT 1 | Blockchain network ID |
| `update_interval` | INTEGER | NOT NULL | Price update interval in seconds |
| `step_decay` | NUMERIC(30,0) | NOT NULL | Raw step decay value in wei |
| `step_decay_rate` | NUMERIC(30,0) | NULL | Step decay rate in RAY format |
| `decay_rate` | NUMERIC(10,4) | NULL | Human-readable decay rate (0.005 = 0.5%) |
| `fixed_starting_price` | NUMERIC(30,0) | NULL | Fixed starting price if set |
| `auction_length` | INTEGER | NULL | Auction duration in seconds |
| `starting_price` | NUMERIC(30,0) | NULL | Dynamic starting price |
| `want_token` | VARCHAR(100) | NULL | Token address being auctioned for |
| `deployer` | VARCHAR(100) | NULL | Address that deployed the contract |
| `receiver` | VARCHAR(100) | NULL | Receiver address |
| `governance` | VARCHAR(100) | NULL | Governance address |
| `discovered_at` | TIMESTAMPTZ | DEFAULT NOW() | When indexer first found this auction |
| `timestamp` | BIGINT | NULL | Unix timestamp when auction was deployed (blockchain time) |
| `factory_address` | VARCHAR(100) | NULL | Factory that deployed this auction |
| `version` | VARCHAR(20) | DEFAULT '0.1.0' | Contract version (0.0.1=legacy, 0.1.0=modern) |

**Primary Key**: `(auction_address, chain_id)`

**Version Detection Logic**:
- Legacy factory → `version = '0.0.1'`
- Modern factory → `version = '0.1.0'`

### `rounds`

**Purpose**: Individual auction rounds created by "kick" events

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `auction_address` | VARCHAR(100) | NOT NULL, PK | Parent auction contract |
| `chain_id` | INTEGER | NOT NULL, PK, DEFAULT 1 | Blockchain network ID |
| `round_id` | INTEGER | NOT NULL, PK | Incremental round ID per auction |
| `from_token` | VARCHAR(100) | NOT NULL | Token being sold in this round |
| `kicked_at` | TIMESTAMPTZ | NOT NULL | When round was started |
| `timestamp` | BIGINT | NOT NULL | Unix timestamp when round was kicked (blockchain time) |
| `initial_available` | NUMERIC(30,0) | NOT NULL | Initial token amount for sale |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether round is still active |
| `current_price` | NUMERIC(30,0) | NULL | Current calculated price |
| `available_amount` | NUMERIC(30,0) | NULL | Remaining tokens available |
| `time_remaining` | INTEGER | NULL | Seconds until round ends |
| `seconds_elapsed` | INTEGER | DEFAULT 0 | Seconds since round started |
| `total_sales` | INTEGER | DEFAULT 0 | Number of takes in this round |
| `total_volume_sold` | NUMERIC(30,0) | DEFAULT 0 | Total tokens sold |
| `progress_percentage` | NUMERIC(5,2) | DEFAULT 0 | Progress 0-100% |
| `block_number` | BIGINT | NOT NULL | Block where round was kicked |
| `transaction_hash` | VARCHAR(100) | NOT NULL | Transaction hash of kick |

**Primary Key**: `(auction_address, chain_id, round_id)`

### `takes`

**Purpose**: Individual "take" transactions within rounds

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `sale_id` | VARCHAR(200) | NOT NULL, PK | Format: {auction}-{roundId}-{saleSeq} |
| `auction_address` | VARCHAR(100) | NOT NULL | Parent auction contract |
| `chain_id` | INTEGER | NOT NULL, DEFAULT 1 | Blockchain network ID |
| `round_id` | INTEGER | NOT NULL | Parent round ID |
| `sale_seq` | INTEGER | NOT NULL | Sequence number within round |
| `taker` | VARCHAR(100) | NOT NULL | Address that made the purchase |
| `from_token` | VARCHAR(100) | NOT NULL | Token purchased |
| `to_token` | VARCHAR(100) | NOT NULL | Token paid (want_token) |
| `amount_taken` | NUMERIC(30,0) | NOT NULL | Amount of from_token purchased |
| `amount_paid` | NUMERIC(30,0) | NOT NULL | Amount of to_token paid |
| `price` | NUMERIC(30,0) | NOT NULL | Price per from_token at time of sale |
| `timestamp` | TIMESTAMPTZ | NOT NULL | When transaction occurred (for hypertable partitioning) |
| `ts_unix` | BIGINT | NOT NULL | Unix timestamp of transaction (blockchain time) |
| `seconds_from_round_start` | INTEGER | NOT NULL | Timing within round |
| `block_number` | BIGINT | NOT NULL | Block number |
| `transaction_hash` | VARCHAR(100) | NOT NULL | Transaction hash |
| `log_index` | INTEGER | NOT NULL | Log index within transaction |

**Primary Key**: `(sale_id, timestamp)`  
**Hypertable**: Partitioned by `timestamp` for time-series optimization

### `tokens`

**Purpose**: Token metadata cache for display purposes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `address` | VARCHAR(100) | NOT NULL | Token contract address |
| `symbol` | VARCHAR(50) | NULL | Token symbol (e.g., "USDC") |
| `name` | VARCHAR(200) | NULL | Full token name |
| `decimals` | INTEGER | NULL | Number of decimal places |
| `chain_id` | INTEGER | NOT NULL, DEFAULT 1 | Blockchain network ID |
| `first_seen` | TIMESTAMPTZ | DEFAULT NOW() | When first discovered |
| `timestamp` | BIGINT | NULL | Unix timestamp when first discovered (blockchain time) |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last updated |

**Unique Constraint**: `(address, chain_id)`

### `price_history`

**Purpose**: Time-series price tracking for charting

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `auction_address` | VARCHAR(100) | NOT NULL | Parent auction |
| `chain_id` | INTEGER | NOT NULL, DEFAULT 1 | Blockchain network ID |
| `round_id` | INTEGER | NOT NULL | Parent round |
| `from_token` | VARCHAR(100) | NOT NULL | Token being priced |
| `timestamp` | TIMESTAMPTZ | NOT NULL | Price observation time (for hypertable partitioning) |
| `ts_unix` | BIGINT | NOT NULL | Unix timestamp of price observation (blockchain time) |
| `price` | NUMERIC(30,0) | NOT NULL | Price at this timestamp |
| `available_amount` | NUMERIC(30,0) | NOT NULL | Tokens available |
| `seconds_from_round_start` | INTEGER | NOT NULL | Timing within round |
| `block_number` | BIGINT | NOT NULL | Block context |

**Hypertable**: Partitioned by `timestamp` for time-series optimization

### `indexer_state`

**Purpose**: Track indexer progress per factory per blockchain network

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `chain_id` | INTEGER | NOT NULL | Blockchain network ID |
| `factory_address` | VARCHAR(100) | NOT NULL | Factory contract address |
| `factory_type` | VARCHAR(10) | NOT NULL | Factory type (legacy/modern) |
| `last_indexed_block` | INTEGER | NOT NULL, DEFAULT 0 | Last processed block for this factory |
| `start_block` | INTEGER | NOT NULL | Starting block for this factory |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

**Unique Constraint**: `(chain_id, factory_address)`

**Rationale**: Each factory on each network may have different deployment blocks and indexing progress. This granular tracking ensures we can:
- Track multiple factories per network independently
- Resume indexing from the correct block per factory
- Handle factory-specific start blocks from configuration

## Views

### `active_auction_rounds`

**Purpose**: Active rounds with calculated time fields

```sql
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    ahp.want_token,
    ahp.decay_rate,
    ahp.update_interval,
    ahp.auction_length,
    ahp.step_decay_rate,
    -- Calculate time remaining
    GREATEST(0, 
        ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
    )::INTEGER as calculated_time_remaining,
    -- Calculate seconds elapsed
    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
FROM rounds ar
JOIN auctions ahp 
    ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;
```

### `recent_takes`

**Purpose**: Recent takes with full token and round context

```sql
CREATE OR REPLACE VIEW recent_takes AS
SELECT 
    als.*,
    ar.kicked_at as round_kicked_at,
    ahp.want_token,
    t1.symbol as from_token_symbol,
    t1.name as from_token_name,
    t1.decimals as from_token_decimals,
    t2.symbol as to_token_symbol,
    t2.name as to_token_name,
    t2.decimals as to_token_decimals
FROM takes als
JOIN rounds ar 
    ON als.auction_address = ar.auction_address 
    AND als.chain_id = ar.chain_id 
    AND als.round_id = ar.round_id
JOIN auctions ahp 
    ON als.auction_address = ahp.auction_address 
    AND als.chain_id = ahp.chain_id
LEFT JOIN tokens t1 
    ON als.from_token = t1.address 
    AND als.chain_id = t1.chain_id
LEFT JOIN tokens t2 
    ON als.to_token = t2.address 
    AND als.chain_id = t2.chain_id
ORDER BY als.timestamp DESC;
```

## Indexes

### Performance Indexes

```sql
-- Auctions
CREATE INDEX idx_auctions_deployer ON auctions (deployer);
CREATE INDEX idx_auctions_factory ON auctions (factory_address);
CREATE INDEX idx_auctions_chain ON auctions (chain_id);

-- Rounds
CREATE INDEX idx_rounds_active ON rounds (is_active);
CREATE INDEX idx_rounds_kicked_at ON rounds (kicked_at);
CREATE INDEX idx_rounds_chain ON rounds (chain_id);
CREATE INDEX idx_rounds_from_token ON rounds (from_token);
CREATE INDEX idx_rounds_active_kicked_at ON rounds (kicked_at DESC) WHERE is_active = TRUE;

-- Takes
CREATE INDEX idx_takes_timestamp ON takes (timestamp);
CREATE INDEX idx_takes_chain ON takes (chain_id);
CREATE INDEX idx_takes_round ON takes (auction_address, chain_id, round_id);
CREATE INDEX idx_takes_taker ON takes (taker);
CREATE INDEX idx_takes_tx_hash ON takes (transaction_hash);
CREATE INDEX idx_takes_recent ON takes (timestamp DESC, auction_address, round_id, sale_seq);

-- Tokens
CREATE INDEX idx_tokens_address ON tokens (address);
CREATE INDEX idx_tokens_chain_id ON tokens (chain_id);

-- Price History
CREATE INDEX idx_price_history_timestamp ON price_history (timestamp);
CREATE INDEX idx_price_history_round ON price_history (auction_address, chain_id, round_id);
CREATE INDEX idx_price_history_chain ON price_history (chain_id);

-- Indexer State
CREATE INDEX idx_indexer_state_chain_factory ON indexer_state (chain_id, factory_address);
CREATE INDEX idx_indexer_state_updated ON indexer_state (updated_at);
```

## Data Types

### Blockchain Values

- **Addresses**: `VARCHAR(100)` - Supports 0x prefix + 40 hex chars + buffer
- **Transaction Hashes**: `VARCHAR(100)` - Same format as addresses  
- **Wei Values**: `NUMERIC(30,0)` - Supports up to 78-digit integers
- **Block Numbers**: `BIGINT` - Sufficient for all current blockchains
- **Chain IDs**: `INTEGER` - Standard network identifiers

### Decimal Precision

- **Human-readable rates**: `NUMERIC(10,4)` - e.g., 0.0050 (0.5%)
- **Percentages**: `NUMERIC(5,2)` - e.g., 99.50 (99.5%)
- **Timestamps**: `TIMESTAMPTZ` - Always timezone-aware

### Version Values

- **Legacy contracts**: `'0.0.1'`
- **Modern contracts**: `'0.1.0'`

## Change Management

### Process for Schema Changes

1. **Update this specification FIRST**
   - Modify column names, types, or constraints here
   - Update version number and last updated date
   - Document reasoning in commit message

2. **Generate migration SQL**
   - Create numbered migration file: `00X_description.sql`
   - Include both schema changes and data migrations
   - Test on copy of production data

3. **Update application code**
   - Indexer: `indexer/indexer.py`
   - API: `monitoring/api/`
   - Frontend: `ui/src/types/`
   - Views and procedures

4. **Update documentation**
   - `CLAUDE.md`
   - API documentation
   - README files

### Backwards Compatibility

When changing column names:
1. Add new column with preferred name
2. Populate with data from old column  
3. Update all application code
4. Drop old column in separate migration
5. Update this specification

### Validation

Before deploying changes:
- [ ] All column names match this specification
- [ ] Indexer inserts use exact column names from spec
- [ ] Views reference correct column names
- [ ] API responses use standardized names
- [ ] Frontend types match database schema

---

**⚠️ IMPORTANT**: This document is the single source of truth for database schema. All changes must be reflected here first before implementation.