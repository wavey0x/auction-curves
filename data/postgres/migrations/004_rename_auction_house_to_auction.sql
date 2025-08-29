-- Migration: Rename auction to auction throughout database schema
-- This changes:
-- 1. Table name: auction_parameters -> auction_parameters
-- 2. Column names: auction_address -> auction_address
-- 3. References and constraints
-- 4. Indexes and views

-- ============================================================================
-- STEP 1: Rename main table
-- ============================================================================

-- Rename auction_parameters table to auction_parameters
ALTER TABLE auction_parameters RENAME TO auction_parameters;

-- ============================================================================
-- STEP 2: Rename column in all related tables
-- ============================================================================

-- Update auction_parameters table (primary)
ALTER TABLE auction_parameters RENAME COLUMN auction_address TO auction_address;

-- Update auction_rounds table
ALTER TABLE auction_rounds RENAME COLUMN auction_address TO auction_address;

-- Update auction_sales table
ALTER TABLE auction_sales RENAME COLUMN auction_address TO auction_address;

-- Update price_history table
ALTER TABLE price_history RENAME COLUMN auction_address TO auction_address;

-- ============================================================================
-- STEP 3: Drop and recreate foreign key constraints with new names
-- ============================================================================

-- Drop existing foreign key constraints
ALTER TABLE auction_rounds DROP CONSTRAINT IF EXISTS auction_rounds_auction_address_chain_id_fkey;
ALTER TABLE auction_sales DROP CONSTRAINT IF EXISTS auction_sales_auction_address_chain_id_round_id_fkey;
ALTER TABLE price_history DROP CONSTRAINT IF EXISTS price_history_auction_address_chain_id_round_id_fkey;

-- Recreate foreign key constraints with new column names
ALTER TABLE auction_rounds 
    ADD CONSTRAINT auction_rounds_auction_address_chain_id_fkey 
    FOREIGN KEY (auction_address, chain_id) 
    REFERENCES auction_parameters(auction_address, chain_id);

ALTER TABLE auction_sales 
    ADD CONSTRAINT auction_sales_auction_address_chain_id_round_id_fkey 
    FOREIGN KEY (auction_address, chain_id, round_id) 
    REFERENCES auction_rounds(auction_address, chain_id, round_id);

ALTER TABLE price_history 
    ADD CONSTRAINT price_history_auction_address_chain_id_round_id_fkey 
    FOREIGN KEY (auction_address, chain_id, round_id) 
    REFERENCES auction_rounds(auction_address, chain_id, round_id);

-- ============================================================================
-- STEP 4: Rename indexes
-- ============================================================================

-- Indexes for auction_parameters (formerly auction_parameters)
DROP INDEX IF EXISTS idx_auction_params_deployer;
DROP INDEX IF EXISTS idx_auction_params_factory;
DROP INDEX IF EXISTS idx_auction_params_chain;

CREATE INDEX idx_auction_params_deployer ON auction_parameters (deployer);
CREATE INDEX idx_auction_params_factory ON auction_parameters (factory_address);
CREATE INDEX idx_auction_params_chain ON auction_parameters (chain_id);

-- Other indexes will be automatically updated by column rename

-- ============================================================================
-- STEP 5: Drop and recreate views with new column names
-- ============================================================================

-- Drop existing views
DROP VIEW IF EXISTS active_auction_rounds CASCADE;
DROP VIEW IF EXISTS recent_auction_sales CASCADE;

-- Recreate active_auction_rounds view with new column names
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    ap.want_token,
    ap.decay_rate_percent,
    ap.update_interval_minutes,
    ap.auction_length,
    ap.step_decay_rate,
    -- Calculate time remaining
    GREATEST(0, 
        ap.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
    )::INTEGER as calculated_time_remaining,
    -- Calculate seconds elapsed
    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
FROM auction_rounds ar
JOIN auction_parameters ap 
    ON ar.auction_address = ap.auction_address 
    AND ar.chain_id = ap.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- Recreate recent_auction_sales view with new column names
CREATE OR REPLACE VIEW recent_auction_sales AS
SELECT 
    als.*,
    ar.kicked_at as round_kicked_at,
    ap.want_token,
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
JOIN auction_parameters ap 
    ON als.auction_address = ap.auction_address 
    AND als.chain_id = ap.chain_id
LEFT JOIN tokens t1 
    ON als.from_token = t1.address 
    AND als.chain_id = t1.chain_id
LEFT JOIN tokens t2 
    ON als.to_token = t2.address 
    AND als.chain_id = t2.chain_id
ORDER BY als.timestamp DESC;

-- ============================================================================
-- STEP 6: Update stored functions and triggers
-- ============================================================================

-- Drop and recreate update_round_statistics function with new column names
DROP FUNCTION IF EXISTS update_round_statistics() CASCADE;
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the auction round statistics
    UPDATE auction_rounds 
    SET 
        total_sales = total_sales + 1,
        total_volume_sold = total_volume_sold + NEW.amount_taken,
        progress_percentage = LEAST(100.0, 
            ((total_volume_sold + NEW.amount_taken) * 100.0) / GREATEST(initial_available, 1)
        ),
        available_amount = GREATEST(0, initial_available - (total_volume_sold + NEW.amount_taken))
    WHERE 
        auction_address = NEW.auction_address 
        AND chain_id = NEW.chain_id 
        AND round_id = NEW.round_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate check_round_expiry function with new column names
DROP FUNCTION IF EXISTS check_round_expiry() CASCADE;
CREATE OR REPLACE FUNCTION check_round_expiry()
RETURNS void AS $$
BEGIN
    UPDATE auction_rounds ar
    SET is_active = FALSE,
        time_remaining = 0
    FROM auction_parameters ap
    WHERE ar.auction_address = ap.auction_address
        AND ar.chain_id = ap.chain_id
        AND ar.is_active = TRUE
        AND ar.kicked_at + (ap.auction_length || ' seconds')::INTERVAL < NOW();
END;
$$ LANGUAGE plpgsql;

-- Recreate trigger
CREATE TRIGGER trigger_update_round_statistics
    AFTER INSERT ON auction_sales
    FOR EACH ROW
    EXECUTE FUNCTION update_round_statistics();

-- ============================================================================
-- STEP 7: Update table comments
-- ============================================================================

COMMENT ON TABLE auction_parameters IS 'Cache of Auction contract parameters (immutable values from deployment)';
COMMENT ON TABLE auction_rounds IS 'Tracks individual rounds within Auctions, created by kick events';
COMMENT ON TABLE auction_sales IS 'Tracks individual sales within rounds, created by take events';
COMMENT ON VIEW active_auction_rounds IS 'Active rounds with calculated time remaining and elapsed time';
COMMENT ON VIEW recent_auction_sales IS 'Recent sales with full token and round context';

-- Note: Column auction_address in all tables now refers to the Auction contract address
-- (formerly called Auction contract address)