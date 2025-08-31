-- Migration 008: Add Unix Timestamp Columns
-- This migration adds unix timestamp columns to all relevant tables
-- to complement existing timestamptz columns for better API performance

-- Add unix timestamp columns to auctions table
ALTER TABLE auctions ADD COLUMN IF NOT EXISTS deployed_at_timestamp BIGINT;

-- Add unix timestamp columns to rounds table  
ALTER TABLE rounds ADD COLUMN IF NOT EXISTS kicked_at_timestamp BIGINT;

-- Add unix timestamp columns to takes table
ALTER TABLE takes ADD COLUMN IF NOT EXISTS unix_timestamp BIGINT;

-- Add unix timestamp columns to tokens table
ALTER TABLE tokens ADD COLUMN IF NOT EXISTS first_seen_timestamp BIGINT;
ALTER TABLE tokens ADD COLUMN IF NOT EXISTS updated_at_timestamp BIGINT;

-- Add unix timestamp columns to price_history table
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS unix_timestamp BIGINT;

-- Add unix timestamp columns to indexer_state table
ALTER TABLE indexer_state ADD COLUMN IF NOT EXISTS updated_at_timestamp BIGINT;

-- Create indexes on new timestamp columns for performance
CREATE INDEX IF NOT EXISTS idx_auctions_deployed_timestamp ON auctions (deployed_at_timestamp);
CREATE INDEX IF NOT EXISTS idx_rounds_kicked_timestamp ON rounds (kicked_at_timestamp);
CREATE INDEX IF NOT EXISTS idx_takes_unix_timestamp ON takes (unix_timestamp);
CREATE INDEX IF NOT EXISTS idx_price_history_unix_timestamp ON price_history (unix_timestamp);

-- Update existing records to populate unix timestamps from existing timestamptz columns
-- This may take some time on large datasets

-- Update auctions table (use discovered_at since deployed timestamp might not be available)
UPDATE auctions 
SET deployed_at_timestamp = EXTRACT(EPOCH FROM discovered_at)::BIGINT 
WHERE deployed_at_timestamp IS NULL;

-- Update rounds table
UPDATE rounds 
SET kicked_at_timestamp = EXTRACT(EPOCH FROM kicked_at)::BIGINT 
WHERE kicked_at_timestamp IS NULL;

-- Update takes table  
UPDATE takes 
SET unix_timestamp = EXTRACT(EPOCH FROM timestamp)::BIGINT 
WHERE unix_timestamp IS NULL;

-- Update tokens table
UPDATE tokens 
SET first_seen_timestamp = EXTRACT(EPOCH FROM first_seen)::BIGINT,
    updated_at_timestamp = EXTRACT(EPOCH FROM updated_at)::BIGINT
WHERE first_seen_timestamp IS NULL;

-- Update price_history table
UPDATE price_history 
SET unix_timestamp = EXTRACT(EPOCH FROM timestamp)::BIGINT 
WHERE unix_timestamp IS NULL;

-- Update indexer_state table
UPDATE indexer_state 
SET updated_at_timestamp = EXTRACT(EPOCH FROM updated_at)::BIGINT 
WHERE updated_at_timestamp IS NULL;

-- Add comments to document the purpose of new columns
COMMENT ON COLUMN auctions.deployed_at_timestamp IS 'Unix timestamp when auction was deployed (for API performance)';
COMMENT ON COLUMN rounds.kicked_at_timestamp IS 'Unix timestamp when round was kicked (for API performance)';
COMMENT ON COLUMN takes.unix_timestamp IS 'Unix timestamp of transaction (for API performance)';
COMMENT ON COLUMN tokens.first_seen_timestamp IS 'Unix timestamp when token was first discovered';
COMMENT ON COLUMN tokens.updated_at_timestamp IS 'Unix timestamp when token was last updated';
COMMENT ON COLUMN price_history.unix_timestamp IS 'Unix timestamp of price observation';
COMMENT ON COLUMN indexer_state.updated_at_timestamp IS 'Unix timestamp of last indexer update';