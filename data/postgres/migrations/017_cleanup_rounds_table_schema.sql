-- Migration 017: Clean up rounds table schema
-- Remove calculated columns and add proper round_start/round_end timestamp columns

-- Drop calculated columns that should not be stored in the database
ALTER TABLE rounds DROP COLUMN IF EXISTS current_price;
ALTER TABLE rounds DROP COLUMN IF EXISTS time_remaining; 
ALTER TABLE rounds DROP COLUMN IF EXISTS seconds_elapsed;

-- Add proper unix timestamp columns for round boundaries
ALTER TABLE rounds ADD COLUMN IF NOT EXISTS round_start BIGINT;
ALTER TABLE rounds ADD COLUMN IF NOT EXISTS round_end BIGINT;

-- Populate round_start with kicked_at unix timestamp
UPDATE rounds 
SET round_start = EXTRACT(EPOCH FROM kicked_at)::BIGINT 
WHERE round_start IS NULL;

-- Populate round_end using auction_length from auctions table
UPDATE rounds 
SET round_end = (
    EXTRACT(EPOCH FROM kicked_at)::BIGINT + 
    COALESCE(a.auction_length, 86400) -- Default to 24 hours if null
)
FROM auctions a 
WHERE rounds.auction_address = a.auction_address 
    AND rounds.chain_id = a.chain_id 
    AND rounds.round_end IS NULL;

-- Add indexes for the new timestamp columns
CREATE INDEX IF NOT EXISTS idx_rounds_round_start ON rounds (round_start);
CREATE INDEX IF NOT EXISTS idx_rounds_round_end ON rounds (round_end);

-- Add comments for the new columns
COMMENT ON COLUMN rounds.round_start IS 'Unix timestamp when round started (same as kicked_at)';
COMMENT ON COLUMN rounds.round_end IS 'Unix timestamp when round ends (round_start + auction_length)';

-- Update schema comments
COMMENT ON TABLE rounds IS 'Tracks individual rounds within Auctions, created by kick events. round_start/round_end are populated by indexer.';