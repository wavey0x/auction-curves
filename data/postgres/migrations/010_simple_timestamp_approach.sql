-- Migration 010: Simple Timestamp Approach
-- Add simple "timestamp" unix timestamp columns alongside existing timestamptz columns

-- Revert previous migration issues and use a cleaner approach

-- For auctions: add simple timestamp column
ALTER TABLE auctions ADD COLUMN IF NOT EXISTS timestamp BIGINT;

-- For rounds: add simple timestamp column  
ALTER TABLE rounds ADD COLUMN IF NOT EXISTS timestamp BIGINT;

-- For takes: we already have unix_timestamp, just rename it
-- But first check if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'takes' AND column_name = 'unix_timestamp') THEN
        ALTER TABLE takes RENAME COLUMN unix_timestamp TO ts_unix;
    END IF;
END $$;
ALTER TABLE takes ADD COLUMN IF NOT EXISTS timestamp BIGINT;

-- For tokens: add simple timestamp column
ALTER TABLE tokens ADD COLUMN IF NOT EXISTS timestamp BIGINT;

-- For price_history: we already have unix_timestamp, handle similarly  
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'price_history' AND column_name = 'unix_timestamp') THEN
        ALTER TABLE price_history RENAME COLUMN unix_timestamp TO ts_unix;
    END IF;
END $$;
ALTER TABLE price_history ADD COLUMN IF NOT EXISTS timestamp BIGINT;

-- Create indexes on new timestamp columns
CREATE INDEX IF NOT EXISTS idx_auctions_timestamp ON auctions (timestamp);
CREATE INDEX IF NOT EXISTS idx_rounds_timestamp ON rounds (timestamp);  
CREATE INDEX IF NOT EXISTS idx_takes_timestamp_unix ON takes (timestamp);
CREATE INDEX IF NOT EXISTS idx_tokens_timestamp ON tokens (timestamp);
CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_unix ON price_history (timestamp);

-- Update comments
COMMENT ON COLUMN auctions.timestamp IS 'Unix timestamp when auction was deployed (blockchain time)';
COMMENT ON COLUMN rounds.timestamp IS 'Unix timestamp when round was kicked (blockchain time)';
COMMENT ON COLUMN takes.timestamp IS 'Unix timestamp of transaction (blockchain time)';
COMMENT ON COLUMN tokens.timestamp IS 'Unix timestamp when token was first discovered';
COMMENT ON COLUMN price_history.timestamp IS 'Unix timestamp of price observation (blockchain time)';