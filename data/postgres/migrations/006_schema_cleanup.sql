-- Migration 006: Schema Cleanup for Custom Indexer
-- Consolidate duplicate columns, add human-readable values, rename columns

-- First drop views that depend on columns we're changing
DROP VIEW IF EXISTS active_auction_rounds;
DROP VIEW IF EXISTS recent_auction_sales;

-- Add new columns with human-readable values
ALTER TABLE auctions ADD COLUMN version VARCHAR(10);
ALTER TABLE auctions ADD COLUMN update_interval INTEGER; -- seconds instead of minutes
ALTER TABLE auctions ADD COLUMN decay_rate DECIMAL(10,8); -- human readable 0.995 instead of 995000000000000000000000000

-- Update data: Convert existing values to human-readable format
UPDATE auctions SET 
    version = auction_version,
    update_interval = price_update_interval,
    decay_rate = 1.0 - (step_decay_rate::DECIMAL / 1000000000000000000000000000);

-- Drop redundant columns
ALTER TABLE auctions DROP COLUMN IF EXISTS auction_version;
ALTER TABLE auctions DROP COLUMN IF EXISTS update_interval_minutes;
ALTER TABLE auctions DROP COLUMN IF EXISTS decay_rate_percent;
ALTER TABLE auctions DROP COLUMN IF EXISTS fixed_starting_price;
ALTER TABLE auctions DROP COLUMN IF EXISTS step_decay;
ALTER TABLE auctions DROP COLUMN IF EXISTS step_decay_rate;

-- Update default value for version column
ALTER TABLE auctions ALTER COLUMN version SET DEFAULT '0.1.0';

-- Update views to use new column names
DROP VIEW IF EXISTS active_auction_rounds;
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    a.want_token,
    a.decay_rate,
    a.update_interval,
    a.auction_length,
    -- Calculate time remaining
    GREATEST(0, 
        a.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
    )::INTEGER as calculated_time_remaining,
    -- Calculate seconds elapsed
    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
FROM auction_rounds ar
JOIN auctions a 
    ON ar.auction_address = a.auction_address 
    AND ar.chain_id = a.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- Update recent sales view
DROP VIEW IF EXISTS recent_auction_sales;
CREATE OR REPLACE VIEW recent_auction_sales AS
SELECT 
    als.*,
    ar.kicked_at as round_kicked_at,
    a.want_token,
    t1.symbol as from_token_symbol,
    t1.name as from_token_name,
    t1.decimals as from_token_decimals,
    t2.symbol as to_token_symbol,
    t2.name as to_token_name,
    t2.decimals as to_token_decimals
FROM auction_sales als
JOIN auction_rounds ar 
    ON als.auction_address = ar.auction_address 
    AND als.chain_id = ar.chain_id 
    AND als.round_id = ar.round_id
JOIN auctions a 
    ON als.auction_address = a.auction_address 
    AND als.chain_id = a.chain_id
LEFT JOIN tokens t1 
    ON als.from_token = t1.address 
    AND als.chain_id = t1.chain_id
LEFT JOIN tokens t2 
    ON als.to_token = t2.address 
    AND als.chain_id = t2.chain_id
ORDER BY als.timestamp DESC;

-- Update comments
COMMENT ON COLUMN auctions.version IS 'Contract version: 0.0.1 (legacy) or 0.1.0 (modern)';
COMMENT ON COLUMN auctions.update_interval IS 'Price update interval in seconds';
COMMENT ON COLUMN auctions.decay_rate IS 'Price decay rate per step (e.g., 0.995 = 0.5% decay)';
COMMENT ON COLUMN auctions.starting_price IS 'Starting price for auctions (in wei, but should be converted to human-readable)';