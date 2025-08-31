-- Migration 005: Custom Indexer Setup
-- Replace Rindexer with custom Web3.py indexer tracking

-- ============================================================================
-- INDEXER STATE TRACKING
-- ============================================================================
-- Track the last indexed block per chain to enable resumable indexing
CREATE TABLE IF NOT EXISTS indexer_state (
    chain_id INTEGER PRIMARY KEY,
    last_indexed_block BIGINT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_indexer_state_updated_at ON indexer_state (updated_at);

-- ============================================================================
-- PERFORMANCE INDEXES FOR EXISTING TABLES
-- ============================================================================
-- Add block number indexes to enable efficient range queries during indexing

-- Auctions table - for tracking when auctions were discovered
CREATE INDEX IF NOT EXISTS idx_auctions_block_chain ON auctions(chain_id, discovered_at);
CREATE INDEX IF NOT EXISTS idx_auctions_factory_chain ON auctions(factory_address, chain_id);

-- Auction rounds table - for efficient block range queries
CREATE INDEX IF NOT EXISTS idx_auction_rounds_block_chain ON auction_rounds(chain_id, block_number);
CREATE INDEX IF NOT EXISTS idx_auction_rounds_kicked_block ON auction_rounds(kicked_at, block_number);

-- Auction sales table - for efficient block range queries  
CREATE INDEX IF NOT EXISTS idx_auction_sales_block_chain ON auction_sales(chain_id, block_number);
CREATE INDEX IF NOT EXISTS idx_auction_sales_tx_log ON auction_sales(transaction_hash, log_index);

-- ============================================================================
-- CLEANUP OLD RINDEXER TABLES
-- ============================================================================
-- Drop any existing Rindexer schemas and tables (if they exist)
-- This is safe to run even if tables don't exist

-- Drop all Rindexer auto-generated schemas
DROP SCHEMA IF EXISTS auctionlocal_auction_factory CASCADE;
DROP SCHEMA IF EXISTS auctionlocal_legacy_auction_factory CASCADE;
DROP SCHEMA IF EXISTS auctionlocal_auction CASCADE;
DROP SCHEMA IF EXISTS auctionlocal_legacy_auction CASCADE;
DROP SCHEMA IF EXISTS auctionlocal_test_auction_1 CASCADE;
DROP SCHEMA IF EXISTS rindexer_internal CASCADE;

-- Drop any standalone Rindexer tables that might exist in public schema
DROP TABLE IF EXISTS deployed_new_auction CASCADE;
DROP TABLE IF EXISTS auction_kicked CASCADE;
DROP TABLE IF EXISTS auction_enabled CASCADE;
DROP TABLE IF EXISTS auction_disabled CASCADE;
DROP TABLE IF EXISTS updated_starting_price CASCADE;
DROP TABLE IF EXISTS updated_step_decay_rate CASCADE;
DROP TABLE IF EXISTS legacy_auction_kicked CASCADE;
DROP TABLE IF EXISTS legacy_auction_enabled CASCADE;
DROP TABLE IF EXISTS legacy_auction_disabled CASCADE;
DROP TABLE IF EXISTS legacy_auction_updated_starting_price CASCADE;

-- ============================================================================
-- INITIALIZE INDEXER STATE FOR DEVELOPMENT
-- ============================================================================
-- Insert default state for local chain (development mode)
-- This will be updated by the indexer when it runs
INSERT INTO indexer_state (chain_id, last_indexed_block) 
VALUES (31337, 0) 
ON CONFLICT (chain_id) DO NOTHING;

-- Add comment for clarity
COMMENT ON TABLE indexer_state IS 'Tracks last indexed block per chain for resumable indexing';
COMMENT ON COLUMN indexer_state.last_indexed_block IS 'Last block number successfully processed by indexer';
COMMENT ON COLUMN indexer_state.updated_at IS 'Timestamp when this chain state was last updated';