-- Migration: Rename auction_parameters to auctions throughout database schema
-- This changes the main auction contracts table name from auction_parameters to auctions

-- ============================================================================
-- STEP 1: Rename main table
-- ============================================================================

-- Rename auction_parameters table to auctions
ALTER TABLE auction_parameters RENAME TO auctions;

-- ============================================================================
-- STEP 2: Drop and recreate foreign key constraints with new table name
-- ============================================================================

-- Drop existing foreign key constraints
ALTER TABLE auction_rounds DROP CONSTRAINT IF EXISTS auction_rounds_auction_address_chain_id_fkey;
ALTER TABLE auction_sales DROP CONSTRAINT IF EXISTS auction_sales_auction_address_chain_id_round_id_fkey;
ALTER TABLE price_history DROP CONSTRAINT IF EXISTS price_history_auction_address_chain_id_round_id_fkey;

-- Recreate foreign key constraints with new table name - DISABLED (not needed)
-- ALTER TABLE auction_rounds 
--     ADD CONSTRAINT auction_rounds_auction_address_chain_id_fkey 
--     FOREIGN KEY (auction_address, chain_id) 
--     REFERENCES auctions(auction_address, chain_id);

-- ALTER TABLE auction_sales 
--     ADD CONSTRAINT auction_sales_auction_address_chain_id_round_id_fkey 
--     FOREIGN KEY (auction_address, chain_id, round_id) 
--     REFERENCES auction_rounds(auction_address, chain_id, round_id);

-- ALTER TABLE price_history 
--     ADD CONSTRAINT price_history_auction_address_chain_id_round_id_fkey 
--     FOREIGN KEY (auction_address, chain_id, round_id) 
--     REFERENCES auction_rounds(auction_address, chain_id, round_id);

-- ============================================================================
-- STEP 3: Rename indexes
-- ============================================================================

-- Indexes for auctions (formerly auction_parameters)
DROP INDEX IF EXISTS idx_auction_params_deployer;
DROP INDEX IF EXISTS idx_auction_params_factory;
DROP INDEX IF EXISTS idx_auction_params_chain;

CREATE INDEX idx_auctions_deployer ON auctions (deployer);
CREATE INDEX idx_auctions_factory ON auctions (factory_address);
CREATE INDEX idx_auctions_chain ON auctions (chain_id);

-- ============================================================================
-- STEP 4: Drop and recreate views with new table name
-- ============================================================================

-- Drop existing views
DROP VIEW IF EXISTS active_auction_rounds CASCADE;
DROP VIEW IF EXISTS recent_auction_sales CASCADE;

-- Recreate active_auction_rounds view with new table name
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    a.want_token,
    a.decay_rate_percent,
    a.update_interval_minutes,
    a.auction_length,
    a.step_decay_rate,
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

-- Recreate recent_auction_sales view with new table name
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

-- ============================================================================
-- STEP 5: Update stored functions and triggers
-- ============================================================================

-- Drop and recreate check_round_expiry function with new table name
DROP FUNCTION IF EXISTS check_round_expiry() CASCADE;
CREATE OR REPLACE FUNCTION check_round_expiry()
RETURNS void AS $$
BEGIN
    UPDATE auction_rounds ar
    SET is_active = FALSE,
        time_remaining = 0
    FROM auctions a
    WHERE ar.auction_address = a.auction_address
        AND ar.chain_id = a.chain_id
        AND ar.is_active = TRUE
        AND ar.kicked_at + (a.auction_length || ' seconds')::INTERVAL < NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 6: Update table comments
-- ============================================================================

COMMENT ON TABLE auctions IS 'Main auction contracts table - one entry per deployed auction contract';
COMMENT ON VIEW active_auction_rounds IS 'Active rounds with calculated time remaining and elapsed time';
COMMENT ON VIEW recent_auction_sales IS 'Recent sales with full token and round context';