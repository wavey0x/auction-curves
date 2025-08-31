-- Migration 003: Remove auction_type concept
-- This migration removes auction type references from the database

\echo 'Running migration 003: Remove auction_type concept'

-- Check if we're running on the correct database
SELECT current_database();

-- ============================================================================
-- REMOVE AUCTION TYPE FROM AUCTION_PARAMETERS TABLE
-- ============================================================================

-- Drop the auction_type index first
DROP INDEX IF EXISTS idx_auction_params_type;

-- Remove the auction_type column
ALTER TABLE auctions DROP COLUMN IF EXISTS auction_type;

-- Update table comment
COMMENT ON TABLE auctions IS 'Auction contract parameters (auction type concept removed)';

-- ============================================================================
-- UPDATE VIEWS TO REMOVE AUCTION TYPE REFERENCES
-- ============================================================================

-- Update active_auction_rounds view to remove auction_type
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    ahp.want_token,
    ahp.decay_rate_percent,
    ahp.update_interval_minutes,
    ahp.auction_length,
    ahp.step_decay_rate,
    -- Calculate time remaining
    GREATEST(0, 
        ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
    )::INTEGER as calculated_time_remaining,
    -- Calculate seconds elapsed
    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
FROM auction_rounds ar
JOIN auctions ahp 
    ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- Update auction_summary view to remove auction_type
CREATE OR REPLACE VIEW auction_summary AS
SELECT 
    ah.*,
    ahp.want_token,
    ahp.decay_rate_percent,
    ahp.update_interval_minutes,
    ahp.auction_length,
    ahp.step_decay_rate,
    -- Current round information
    ar.round_id as current_round_id,
    ar.kicked_at as current_round_started,
    ar.is_active as has_active_round,
    ar.initial_available as current_initial_available,
    ar.current_available,
    ar.total_sales as current_round_sales,
    -- Time calculations
    CASE 
        WHEN ar.is_active THEN 
            GREATEST(0, ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at)))::INTEGER
        ELSE 0 
    END as time_remaining_seconds,
    CASE 
        WHEN ar.is_active THEN 
            EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER
        ELSE 0 
    END as seconds_elapsed
FROM auctions ah
LEFT JOIN auctions ahp 
    ON ah.address = ahp.auction_address 
    AND ah.chain_id = ahp.chain_id
LEFT JOIN auction_rounds ar 
    ON ah.address = ar.auction_address 
    AND ah.chain_id = ar.chain_id 
    AND ar.is_active = TRUE
ORDER BY ah.deployed_at DESC;

\echo 'Migration 003 completed successfully'
\echo 'Auction type concept has been completely removed from the database'