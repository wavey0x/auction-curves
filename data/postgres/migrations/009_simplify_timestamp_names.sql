-- Migration 009: Simplify Timestamp Column Names
-- Rename verbose timestamp column names to simple "timestamp" and clean up naming

-- Drop the verbose columns and replace with simple names
ALTER TABLE auctions DROP COLUMN IF EXISTS deployed_at_timestamp;
ALTER TABLE auctions ADD COLUMN timestamp BIGINT;

-- For rounds: rename kicked_at_timestamp to timestamp  
ALTER TABLE rounds DROP COLUMN IF EXISTS kicked_at_timestamp;
ALTER TABLE rounds ADD COLUMN timestamp BIGINT;

-- For takes: rename unix_timestamp to timestamp (it already exists as "timestamp" timestamptz)
-- We need to rename the unix_timestamp to just timestamp, but we already have a timestamptz "timestamp" 
-- So we'll drop the existing timestamptz timestamp and use timestamp as the unix timestamp
ALTER TABLE takes DROP COLUMN timestamp;
ALTER TABLE takes RENAME COLUMN unix_timestamp TO timestamp;

-- For tokens: remove verbose timestamp names, keep updated_at
ALTER TABLE tokens DROP COLUMN IF EXISTS first_seen_timestamp;
ALTER TABLE tokens DROP COLUMN IF EXISTS updated_at_timestamp;
ALTER TABLE tokens ADD COLUMN timestamp BIGINT;

-- For price_history: rename unix_timestamp to timestamp (similar issue as takes)
ALTER TABLE price_history DROP COLUMN timestamp;
ALTER TABLE price_history RENAME COLUMN unix_timestamp TO timestamp;

-- For indexer_state: remove verbose name, keep updated_at
ALTER TABLE indexer_state DROP COLUMN IF EXISTS updated_at_timestamp;

-- Update indexes to use new column names
DROP INDEX IF EXISTS idx_auctions_deployed_timestamp;
DROP INDEX IF EXISTS idx_rounds_kicked_timestamp;
DROP INDEX IF EXISTS idx_takes_unix_timestamp;  
DROP INDEX IF EXISTS idx_price_history_unix_timestamp;

CREATE INDEX idx_auctions_timestamp ON auctions (timestamp);
CREATE INDEX idx_rounds_timestamp ON rounds (timestamp);
CREATE INDEX idx_takes_timestamp ON takes (timestamp);
CREATE INDEX idx_price_history_timestamp ON price_history (timestamp);
CREATE INDEX idx_tokens_timestamp ON tokens (timestamp);

-- Update comments
COMMENT ON COLUMN auctions.timestamp IS 'Unix timestamp when auction was deployed (blockchain time)';
COMMENT ON COLUMN rounds.timestamp IS 'Unix timestamp when round was kicked (blockchain time)';
COMMENT ON COLUMN takes.timestamp IS 'Unix timestamp of transaction (blockchain time)';
COMMENT ON COLUMN tokens.timestamp IS 'Unix timestamp when token was first discovered';
COMMENT ON COLUMN price_history.timestamp IS 'Unix timestamp of price observation (blockchain time)';