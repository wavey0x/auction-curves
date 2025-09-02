# Auction System Database Specification

**Version**: 2.0  
**Last Updated**: 2025-09-01  
**Status**: AUTHORITATIVE MASTER SPECIFICATION

**IMPORTANT**: This document represents the CURRENT database schema only. No historical changes or deprecated columns are documented here. For migration history, see the migrations folder.

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

| Concept | STANDARD NAME |
|---------|---------------|
| Version | `version` |
| Decay Rate | `decay_rate` |  
| Update Interval | `update_interval` |
| Take ID | `take_id` |
| Take Sequence | `take_seq` |

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
| `factory_address` | VARCHAR(100) | NULL | Factory that deployed this auction |
| `version` | VARCHAR(20) | DEFAULT '0.1.0' | Contract version |
| `timestamp` | BIGINT | NOT NULL, DEFAULT EXTRACT(epoch FROM now()) | Unix timestamp when deployed |

**Primary Key**: `(auction_address, chain_id)`

### `rounds`

**Purpose**: Individual auction rounds created by "kick" events

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `auction_address` | VARCHAR(100) | NOT NULL, PK | Parent auction contract |
| `chain_id` | INTEGER | NOT NULL, PK, DEFAULT 1 | Blockchain network ID |
| `round_id` | INTEGER | NOT NULL, PK | Incremental round ID per auction |
| `from_token` | VARCHAR(100) | NOT NULL | Token being sold in this round |
| `initial_available` | NUMERIC(78,18) | NOT NULL | Initial token amount for sale |
| `available_amount` | NUMERIC(78,18) | NULL | Remaining tokens available |
| `total_takes` | INTEGER | DEFAULT 0 | Number of takes in this round |
| `total_volume_sold` | NUMERIC(78,18) | DEFAULT 0 | Total tokens sold |
| `progress_percentage` | NUMERIC(5,2) | DEFAULT 0 | Progress 0-100% |
| `block_number` | BIGINT | NOT NULL | Block where round was kicked |
| `transaction_hash` | VARCHAR(200) | NOT NULL | Transaction hash of kick |
| `kicked_at` | BIGINT | NOT NULL | Unix timestamp when round was kicked |
| `timestamp` | BIGINT | NOT NULL, DEFAULT EXTRACT(epoch FROM now()) | Record creation timestamp |
| `round_start` | BIGINT | NULL | Unix timestamp when round started |
| `round_end` | BIGINT | NULL | Unix timestamp when round ends |

**Primary Key**: `(auction_address, chain_id, round_id)`

**Note**: `is_active` is calculated dynamically in views based on `round_end > current_time AND available_amount > 0`

### `takes`

**Purpose**: Individual "take" transactions within rounds

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `take_id` | VARCHAR(200) | NOT NULL, PK | Format: {auction}-{roundId}-{takeSeq} |
| `auction_address` | VARCHAR(100) | NOT NULL | Parent auction contract |
| `chain_id` | INTEGER | NOT NULL, DEFAULT 1 | Blockchain network ID |
| `round_id` | INTEGER | NOT NULL | Parent round ID |
| `take_seq` | INTEGER | NOT NULL | Sequence number within round |
| `taker` | VARCHAR(100) | NOT NULL | Address that made the purchase |
| `from_token` | VARCHAR(100) | NOT NULL | Token purchased |
| `to_token` | VARCHAR(100) | NOT NULL | Token paid (want_token) |
| `amount_taken` | NUMERIC(78,18) | NOT NULL | Amount of from_token purchased |
| `amount_paid` | NUMERIC(78,18) | NOT NULL | Amount of to_token paid |
| `price` | NUMERIC(78,18) | NOT NULL | Price per from_token at time of take |
| `timestamp` | TIMESTAMPTZ | NOT NULL | When transaction occurred (for hypertable partitioning) |
| `seconds_from_round_start` | INTEGER | NOT NULL | Timing within round |
| `block_number` | BIGINT | NOT NULL | Block number |
| `transaction_hash` | VARCHAR(200) | NOT NULL | Transaction hash |
| `log_index` | INTEGER | NOT NULL | Log index within transaction |

**Primary Key**: `(take_id, timestamp)`  
**Hypertable**: Partitioned by `timestamp` for time-series optimization (TimescaleDB)

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
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last updated |
| `timestamp` | BIGINT | NULL | Unix timestamp when first discovered |

**Unique Constraints**: `(address)`, `(address, chain_id)`

### `enabled_tokens`

**Purpose**: Track which tokens are enabled for each auction

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `auction_address` | VARCHAR(100) | NOT NULL, PK | Parent auction contract |
| `chain_id` | INTEGER | NOT NULL, PK, DEFAULT 1 | Blockchain network ID |
| `token_address` | VARCHAR(100) | NOT NULL, PK | Enabled token address |
| `enabled_at` | BIGINT | NOT NULL | Unix timestamp when enabled |
| `enabled_at_block` | BIGINT | NOT NULL | Block number when enabled |
| `enabled_at_tx_hash` | VARCHAR(100) | NOT NULL | Transaction hash of enable event |

**Primary Key**: `(auction_address, chain_id, token_address)`
**Foreign Key**: `REFERENCES auctions(auction_address, chain_id) ON DELETE CASCADE`

### `price_requests`

**Purpose**: Track price fetch requests for tokens

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `chain_id` | INTEGER | NOT NULL | Blockchain network ID |
| `block_number` | BIGINT | NOT NULL | Block number that triggered request |
| `token_address` | VARCHAR(100) | NOT NULL | Token to fetch price for |
| `request_type` | VARCHAR(20) | NOT NULL, CHECK('kick', 'take') | Event type that triggered request |
| `auction_address` | VARCHAR(100) | NULL | Related auction address |
| `round_id` | INTEGER | NULL | Related round ID |
| `status` | VARCHAR(20) | DEFAULT 'pending', CHECK('pending', 'processing', 'completed', 'failed') | Request status |
| `created_at` | TIMESTAMP | DEFAULT NOW() | When request was created |
| `processed_at` | TIMESTAMP | NULL | When request was processed |
| `error_message` | TEXT | NULL | Error details if failed |
| `retry_count` | INTEGER | DEFAULT 0 | Number of retry attempts |

**Unique Constraint**: `(chain_id, block_number, token_address)`

### `token_prices`

**Purpose**: Store historical token prices in USD

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| `chain_id` | INTEGER | NOT NULL | Blockchain network ID |
| `block_number` | BIGINT | NOT NULL | Block number for price |
| `token_address` | VARCHAR(100) | NOT NULL | Token contract address |
| `price_usd` | NUMERIC(40,18) | NOT NULL | Token price in USD with high precision |
| `timestamp` | BIGINT | NOT NULL | Unix timestamp of price |
| `source` | VARCHAR(50) | NOT NULL, DEFAULT 'ypricemagic' | Price data source |
| `created_at` | TIMESTAMP | DEFAULT NOW() | When record was created |

**Unique Constraint**: `(chain_id, block_number, token_address, source)`

> Note: The previously proposed `price_history` table has been removed as unused. Price history is computed on-demand by the API/service when needed.

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

## Views

### `vw_rounds`

**Purpose**: Rounds with calculated time fields and token metadata

```sql
WITH base AS (
  SELECT ar.auction_address, ar.chain_id, ar.round_id, ar.from_token,
         ar.kicked_at, ar.initial_available, ar.available_amount,
         ar.total_takes, ar.total_volume_sold, ar.block_number,
         ar.transaction_hash, ahp.want_token, ahp.auction_length, ar.round_end
  FROM rounds ar
  JOIN auctions ahp ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
)
SELECT b.*, 
  tf.symbol AS from_symbol, tf.name AS from_name, tf.decimals AS from_decimals,
  tw.symbol AS want_symbol, tw.name AS want_name, tw.decimals AS want_decimals,
  GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER AS time_remaining,
  GREATEST(0, b.auction_length - GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER) AS seconds_elapsed,
  (GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER > 0 AND COALESCE(b.available_amount, 0) > 0) AS is_active
FROM base b
LEFT JOIN tokens tf ON LOWER(tf.address) = LOWER(b.from_token) AND tf.chain_id = b.chain_id
LEFT JOIN tokens tw ON LOWER(tw.address) = LOWER(b.want_token) AND tw.chain_id = b.chain_id
```

### `vw_active_rounds`

**Purpose**: Active rounds only (where is_active = true)

```sql
SELECT * FROM vw_rounds 
WHERE is_active = true 
ORDER BY kicked_at DESC
```

### `vw_takes`

**Purpose**: Takes with full token and round context

```sql
SELECT als.take_id, als.auction_address, als.chain_id, als.round_id, als.take_seq,
       als.taker, als.from_token, als.to_token, als.amount_taken, als.amount_paid,
       als.price, als.timestamp, als.seconds_from_round_start, als.block_number,
       als.transaction_hash, als.log_index, ar.kicked_at AS round_kicked_at,
       tf.symbol AS from_symbol, tf.name AS from_name, tf.decimals AS from_decimals,
       tw.symbol AS to_symbol, tw.name AS to_name, tw.decimals AS to_decimals
FROM takes als
LEFT JOIN rounds ar ON als.auction_address = ar.auction_address 
  AND als.chain_id = ar.chain_id AND als.round_id = ar.round_id
LEFT JOIN tokens tf ON LOWER(tf.address) = LOWER(als.from_token) AND tf.chain_id = als.chain_id
LEFT JOIN tokens tw ON LOWER(tw.address) = LOWER(als.to_token) AND tw.chain_id = als.chain_id
```

## Indexes

### Performance Indexes

```sql
-- Auctions
CREATE INDEX idx_auctions_deployer ON auctions (deployer);
CREATE INDEX idx_auctions_factory ON auctions (factory_address);
CREATE INDEX idx_auctions_chain ON auctions (chain_id);
CREATE INDEX idx_auctions_address_chain ON auctions (auction_address, chain_id);
CREATE INDEX idx_auctions_timestamp ON auctions (timestamp);

-- Rounds
CREATE INDEX idx_rounds_kicked_at ON rounds (kicked_at);
CREATE INDEX idx_rounds_chain ON rounds (chain_id);
CREATE INDEX idx_rounds_from_token ON rounds (from_token);
CREATE INDEX idx_rounds_round_end ON rounds (round_end);
CREATE INDEX idx_rounds_round_start ON rounds (round_start);
CREATE INDEX idx_rounds_timestamp ON rounds (timestamp);

-- Takes
CREATE INDEX idx_takes_timestamp ON takes (timestamp);
CREATE INDEX idx_takes_chain ON takes (chain_id);
CREATE INDEX idx_takes_round ON takes (auction_address, chain_id, round_id);
CREATE INDEX idx_takes_taker ON takes (taker);
CREATE INDEX idx_takes_tx_hash ON takes (transaction_hash);
CREATE INDEX idx_takes_recent ON takes (timestamp DESC, auction_address, round_id, take_seq);
CREATE INDEX idx_takes_auction_chain_timestamp ON takes (auction_address, chain_id, timestamp DESC);
CREATE INDEX idx_takes_timestamp_unix ON takes (timestamp);
CREATE UNIQUE INDEX idx_takes_unique_chain_tx_log_ts ON takes (chain_id, transaction_hash, log_index, timestamp);

-- Tokens
CREATE INDEX idx_tokens_address ON tokens (address);
CREATE INDEX idx_tokens_chain_id ON tokens (chain_id);
CREATE INDEX idx_tokens_lower_address_chain ON tokens (LOWER(address), chain_id);
CREATE INDEX idx_tokens_timestamp ON tokens (timestamp);

-- Enabled Tokens
CREATE INDEX idx_enabled_tokens_auction ON enabled_tokens (auction_address, chain_id);
CREATE INDEX idx_enabled_tokens_token ON enabled_tokens (token_address, chain_id);
CREATE INDEX idx_enabled_tokens_enabled_at ON enabled_tokens (enabled_at);

-- Price Requests
CREATE INDEX idx_price_requests_chain_token ON price_requests (chain_id, token_address);
CREATE INDEX idx_price_requests_status ON price_requests (status);
CREATE INDEX idx_price_requests_created ON price_requests (created_at DESC);

-- Token Prices
CREATE INDEX idx_token_prices_lookup ON token_prices (chain_id, token_address, block_number DESC);
CREATE INDEX idx_token_prices_chain_block ON token_prices (chain_id, block_number DESC);
CREATE INDEX idx_token_prices_timestamp ON token_prices (timestamp DESC);
CREATE INDEX idx_token_prices_source ON token_prices (source);

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
- **Transaction Hashes**: `VARCHAR(200)` - Extended for various blockchain formats
- **Token Amounts**: `NUMERIC(78,18)` - High precision for token values
- **Wei Values**: `NUMERIC(30,0)` - Raw blockchain values
- **Block Numbers**: `BIGINT` - Sufficient for all current blockchains
- **Chain IDs**: `INTEGER` - Standard network identifiers

### Decimal Precision

- **Human-readable rates**: `NUMERIC(10,4)` - e.g., 0.0050 (0.5%)
- **Percentages**: `NUMERIC(5,2)` - e.g., 99.50 (99.5%)
- **Timestamps**: `TIMESTAMPTZ` - Always timezone-aware for PostgreSQL timestamps
- **Unix Timestamps**: `BIGINT` - Blockchain time values
- **USD Prices**: `NUMERIC(40,18)` - High precision for price data

### Contract Versions

- **Legacy contracts**: `'0.0.1'`
- **Modern contracts**: `'0.1.0'`

## Change Management

### Process for Schema Changes

1. **Update this specification FIRST**
   - Modify table definitions to reflect new current state
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

### Validation

Before deploying changes:
- [ ] All column names match this specification exactly
- [ ] Indexer inserts use exact column names from spec
- [ ] Views reference correct column names
- [ ] API responses use standardized names
- [ ] Frontend types match database schema
- [ ] All indexes are created as specified
- [ ] Constraints are properly defined

---

**⚠️ IMPORTANT**: This document is the single source of truth for the current database schema. All code changes must reference this specification.
