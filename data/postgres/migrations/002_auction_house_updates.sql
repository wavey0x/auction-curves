-- Migration 002: Auction Contract Updates
-- This migration updates the schema to reflect changes from ParameterizedAuction to Auction

\echo 'Running migration 002: Auction Contract Updates'

-- Check if we're running on the correct database
SELECT current_database();

-- ============================================================================
-- UPDATE AUCTION PARAMETERS TABLE
-- ============================================================================

-- Add new stepDecayRate field (replaces step_decay)
ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS step_decay_rate DECIMAL(30,0);

-- Update comments to reflect Auction contract
COMMENT ON TABLE auctions IS 'Cache of Auction contract parameters (renamed from ParameterizedAuction)';
COMMENT ON COLUMN auctions.step_decay_rate IS 'Step decay rate per 36-second step (e.g., 0.995 * 1e27 for 0.5% decay)';
COMMENT ON COLUMN auctions.step_decay IS 'DEPRECATED: Use step_decay_rate instead';

-- Copy data from step_decay to step_decay_rate if not already done
UPDATE auctions 
SET step_decay_rate = step_decay 
WHERE step_decay_rate IS NULL AND step_decay IS NOT NULL;

-- ============================================================================
-- RINDEXER TABLE REFERENCES UPDATE
-- ============================================================================
-- Update comments to reflect the new UpdatedStepDecayRate event

COMMENT ON SCHEMA public IS 'Updated for Auction contract changes:
- Added support for UpdatedStepDecayRate event
- Updated variable names from ParameterizedAuction to Auction
- AUCTION_LENGTH is now an immutable constant
- stepDecayRate is now a storage variable
- STEP_DURATION is now a constant (36 seconds)
';

-- ============================================================================
-- UPDATE DATABASE DOCUMENTATION
-- ============================================================================

-- Note: The following NEW Rindexer table will be created automatically:
-- 
-- - updated_step_decay_rate (from UpdatedStepDecayRate event)
--   * step_decay_rate (uint256) - indexed
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- This supplements the existing updated_starting_price table

-- ============================================================================
-- CREATE INDEX FOR NEW EVENT TABLE
-- ============================================================================

-- Create index for the new step decay rate event table (when it's created by Rindexer)
-- Note: This will be executed after Rindexer creates the table
CREATE OR REPLACE FUNCTION create_step_decay_rate_index()
RETURNS void AS $$
BEGIN
    -- Check if the table exists before creating index
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'updated_step_decay_rate') THEN
        CREATE INDEX IF NOT EXISTS idx_updated_step_decay_rate_timestamp 
            ON updated_step_decay_rate (timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_updated_step_decay_rate_chain 
            ON updated_step_decay_rate (chain_id);
        CREATE INDEX IF NOT EXISTS idx_updated_step_decay_rate_decay_rate 
            ON updated_step_decay_rate (step_decay_rate);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UPDATE VIEWS TO HANDLE NEW FIELDS
-- ============================================================================

-- Update active_auction_rounds view to use new field names
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    ahp.want_token,
    ahp.auction_type,
    ahp.decay_rate_percent,
    ahp.update_interval_minutes,
    ahp.auction_length,
    ahp.step_decay_rate, -- Include new field
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

-- ============================================================================
-- BACKWARD COMPATIBILITY FUNCTION
-- ============================================================================

-- Function to sync step_decay_rate changes back to step_decay for compatibility
CREATE OR REPLACE FUNCTION sync_step_decay_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- If step_decay_rate is updated, sync it to step_decay for backward compatibility
    IF NEW.step_decay_rate IS DISTINCT FROM OLD.step_decay_rate THEN
        NEW.step_decay = NEW.step_decay_rate;
    END IF;
    
    -- If step_decay is updated, sync it to step_decay_rate
    IF NEW.step_decay IS DISTINCT FROM OLD.step_decay THEN
        NEW.step_decay_rate = NEW.step_decay;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to keep fields in sync during transition period
DROP TRIGGER IF EXISTS trigger_sync_step_decay_fields ON auctions;
CREATE TRIGGER trigger_sync_step_decay_fields
    BEFORE UPDATE ON auctions
    FOR EACH ROW
    EXECUTE FUNCTION sync_step_decay_fields();

\echo 'Migration 002 completed successfully'
\echo 'Note: Run create_step_decay_rate_index() after Rindexer creates the updated_step_decay_rate table'