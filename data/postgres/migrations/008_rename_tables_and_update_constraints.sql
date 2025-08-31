-- Migration 008: Rename tables and update constraints
-- Rename auction_rounds -> rounds, auction_sales -> takes
-- Remove foreign key constraints and increase column sizes for robustness

-- First, drop any existing foreign key constraints (should already be commented out)
-- No need to drop as they are already removed in current schema

-- Drop existing views that reference the old table names
DROP VIEW IF EXISTS active_auction_rounds;
DROP VIEW IF EXISTS recent_auction_sales;

-- Drop existing triggers that reference the old table names
DROP TRIGGER IF EXISTS trigger_update_round_statistics ON auction_sales;
DROP FUNCTION IF EXISTS update_round_statistics();

-- Rename tables
ALTER TABLE auction_rounds RENAME TO rounds;
ALTER TABLE auction_sales RENAME TO takes;

-- Update column sizes for robustness
-- auction_address fields: VARCHAR(42) -> VARCHAR(100)
ALTER TABLE rounds ALTER COLUMN auction_address TYPE VARCHAR(100);
ALTER TABLE takes ALTER COLUMN auction_address TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN auction_address TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN want_token TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN deployer TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN receiver TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN governance TYPE VARCHAR(100);
ALTER TABLE auctions ALTER COLUMN factory_address TYPE VARCHAR(100);
ALTER TABLE tokens ALTER COLUMN address TYPE VARCHAR(100);

-- from_token/to_token fields: VARCHAR(42) -> VARCHAR(100)
ALTER TABLE rounds ALTER COLUMN from_token TYPE VARCHAR(100);
ALTER TABLE takes ALTER COLUMN from_token TYPE VARCHAR(100);
ALTER TABLE takes ALTER COLUMN to_token TYPE VARCHAR(100);
ALTER TABLE price_history ALTER COLUMN auction_address TYPE VARCHAR(100);
ALTER TABLE price_history ALTER COLUMN from_token TYPE VARCHAR(100);

-- transaction_hash fields: VARCHAR(66) -> VARCHAR(100)
ALTER TABLE rounds ALTER COLUMN transaction_hash TYPE VARCHAR(100);
ALTER TABLE takes ALTER COLUMN transaction_hash TYPE VARCHAR(100);

-- taker field: VARCHAR(42) -> VARCHAR(100)
ALTER TABLE takes ALTER COLUMN taker TYPE VARCHAR(100);

-- sale_id field: VARCHAR(100) -> VARCHAR(200)
ALTER TABLE takes ALTER COLUMN sale_id TYPE VARCHAR(200);

-- version field: VARCHAR(10) -> VARCHAR(20)
ALTER TABLE auctions ALTER COLUMN auction_version TYPE VARCHAR(20);

-- token name/symbol fields for extra room
ALTER TABLE tokens ALTER COLUMN symbol TYPE VARCHAR(50);
ALTER TABLE tokens ALTER COLUMN name TYPE VARCHAR(200);

-- Recreate the trigger function with new table names
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the round statistics
    UPDATE rounds 
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

-- Recreate trigger with new table name
CREATE TRIGGER trigger_update_round_statistics
    AFTER INSERT ON takes
    FOR EACH ROW
    EXECUTE FUNCTION update_round_statistics();

-- Update the round expiry function to use new table name
CREATE OR REPLACE FUNCTION check_round_expiry()
RETURNS void AS $$
BEGIN
    UPDATE rounds ar
    SET is_active = FALSE,
        time_remaining = 0
    FROM auctions ahp
    WHERE ar.auction_address = ahp.auction_address
        AND ar.chain_id = ahp.chain_id
        AND ar.is_active = TRUE
        AND ar.kicked_at + (ahp.auction_length || ' seconds')::INTERVAL < NOW();
END;
$$ LANGUAGE plpgsql;

-- Recreate views with new table names
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
FROM rounds ar
JOIN auctions ahp 
    ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- View for recent takes with full context (renamed from recent_auction_sales)
CREATE OR REPLACE VIEW recent_takes AS
SELECT 
    als.*,
    ar.kicked_at as round_kicked_at,
    ahp.want_token,
    t1.symbol as from_token_symbol,
    t1.name as from_token_name,
    t1.decimals as from_token_decimals,
    t2.symbol as to_token_symbol,
    t2.name as to_token_name,
    t2.decimals as to_token_decimals
FROM takes als
JOIN rounds ar 
    ON als.auction_address = ar.auction_address 
    AND als.chain_id = ar.chain_id 
    AND als.round_id = ar.round_id
JOIN auctions ahp 
    ON als.auction_address = ahp.auction_address 
    AND als.chain_id = ahp.chain_id
LEFT JOIN tokens t1 
    ON als.from_token = t1.address 
    AND als.chain_id = t1.chain_id
LEFT JOIN tokens t2 
    ON als.to_token = t2.address 
    AND als.chain_id = t2.chain_id
ORDER BY als.timestamp DESC;

-- Update table comments
COMMENT ON TABLE rounds IS 'Tracks individual rounds within Auctions, created by kick events (renamed from auction_rounds)';
COMMENT ON TABLE takes IS 'Tracks individual takes within rounds, created by take events (renamed from auction_sales)';
COMMENT ON VIEW active_auction_rounds IS 'Active rounds with calculated time remaining and elapsed time';
COMMENT ON VIEW recent_takes IS 'Recent takes with full token and round context (renamed from recent_auction_sales)';

-- Update indexes that might have been affected by table renames
-- Drop old indexes if they exist (some may have been auto-renamed)
DROP INDEX IF EXISTS idx_auction_rounds_active;
DROP INDEX IF EXISTS idx_auction_rounds_kicked_at;
DROP INDEX IF EXISTS idx_auction_rounds_chain;
DROP INDEX IF EXISTS idx_auction_rounds_from_token;
DROP INDEX IF EXISTS idx_auction_rounds_active_kicked_at;
DROP INDEX IF EXISTS idx_auction_sales_timestamp;
DROP INDEX IF EXISTS idx_auction_sales_chain;
DROP INDEX IF EXISTS idx_auction_sales_round;
DROP INDEX IF EXISTS idx_auction_sales_taker;
DROP INDEX IF EXISTS idx_auction_sales_tx_hash;
DROP INDEX IF EXISTS idx_auction_sales_recent;

-- Recreate indexes with new names
CREATE INDEX idx_rounds_active ON rounds (is_active);
CREATE INDEX idx_rounds_kicked_at ON rounds (kicked_at);
CREATE INDEX idx_rounds_chain ON rounds (chain_id);
CREATE INDEX idx_rounds_from_token ON rounds (from_token);
CREATE INDEX idx_rounds_active_kicked_at ON rounds (kicked_at DESC) WHERE is_active = TRUE;

CREATE INDEX idx_takes_timestamp ON takes (timestamp);
CREATE INDEX idx_takes_chain ON takes (chain_id);
CREATE INDEX idx_takes_round ON takes (auction_address, chain_id, round_id);
CREATE INDEX idx_takes_taker ON takes (taker);
CREATE INDEX idx_takes_tx_hash ON takes (transaction_hash);
CREATE INDEX idx_takes_recent ON takes (timestamp DESC, auction_address, round_id, sale_seq);

-- Verify the rename worked
DO $$
BEGIN
    -- Check if tables exist
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'rounds') THEN
        RAISE EXCEPTION 'Table rounds does not exist after migration';
    END IF;
    
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'takes') THEN
        RAISE EXCEPTION 'Table takes does not exist after migration';
    END IF;
    
    -- Check if old tables don't exist
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'auction_rounds') THEN
        RAISE EXCEPTION 'Old table auction_rounds still exists after migration';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'auction_sales') THEN
        RAISE EXCEPTION 'Old table auction_sales still exists after migration';
    END IF;
    
    RAISE NOTICE 'Migration 008 completed successfully: Tables renamed and constraints updated';
END
$$;