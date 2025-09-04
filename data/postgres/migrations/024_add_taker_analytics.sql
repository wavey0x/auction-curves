-- Migration 024: Add USD columns and taker analytics
-- This migration adds USD value columns to the takes table and creates
-- a materialized view for taker rankings and statistics

BEGIN;

-- Add USD columns to takes table
ALTER TABLE takes ADD COLUMN IF NOT EXISTS amount_taken_usd NUMERIC(30,10);
ALTER TABLE takes ADD COLUMN IF NOT EXISTS amount_paid_usd NUMERIC(30,10);
ALTER TABLE takes ADD COLUMN IF NOT EXISTS from_token_price_usd NUMERIC(30,10);
ALTER TABLE takes ADD COLUMN IF NOT EXISTS to_token_price_usd NUMERIC(30,10);

-- Create materialized view for taker rankings and summary statistics
DROP MATERIALIZED VIEW IF EXISTS vw_takers_summary;

CREATE MATERIALIZED VIEW vw_takers_summary AS
SELECT 
    taker,
    COUNT(*) as total_takes,
    COUNT(DISTINCT auction_address) as unique_auctions,
    COUNT(DISTINCT chain_id) as unique_chains,
    COALESCE(SUM(amount_taken_usd), 0) as total_volume_usd,
    COALESCE(AVG(amount_taken_usd), 0) as avg_take_size_usd,
    MIN(timestamp) as first_take,
    MAX(timestamp) as last_take,
    ARRAY_AGG(DISTINCT chain_id ORDER BY chain_id) as active_chains,
    -- Rankings will be calculated at query time for better performance
    0 as rank_by_takes,
    0 as rank_by_volume
FROM takes
WHERE taker IS NOT NULL
GROUP BY taker
HAVING COUNT(*) > 0;

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_takes_taker_volume ON takes(taker, amount_taken_usd) WHERE amount_taken_usd IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_takes_taker_timestamp ON takes(taker, timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vw_takers_summary_taker ON vw_takers_summary(taker);
CREATE INDEX IF NOT EXISTS idx_vw_takers_summary_volume ON vw_takers_summary(total_volume_usd DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_vw_takers_summary_takes ON vw_takers_summary(total_takes DESC);
CREATE INDEX IF NOT EXISTS idx_vw_takers_summary_recent ON vw_takers_summary(last_take DESC NULLS LAST);

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_takers_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY vw_takers_summary;
END;
$$ LANGUAGE plpgsql;

-- Add comment for documentation
COMMENT ON MATERIALIZED VIEW vw_takers_summary IS 'Aggregated statistics for all takers including rankings, volume metrics, and activity timelines. Refreshed hourly.';

-- Insert verification data
DO $verification$
DECLARE
    takes_count INTEGER;
    takers_count INTEGER;
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO takes_count FROM takes;
    SELECT COUNT(DISTINCT taker) INTO takers_count FROM takes WHERE taker IS NOT NULL;
    SELECT COUNT(*) INTO view_count FROM vw_takers_summary;
    
    RAISE NOTICE 'Migration 024 completed successfully:';
    RAISE NOTICE '  - Total takes: %', takes_count;
    RAISE NOTICE '  - Unique takers: %', takers_count;
    RAISE NOTICE '  - Takers in summary view: %', view_count;
    RAISE NOTICE '  - Added USD columns: amount_taken_usd, amount_paid_usd, from_token_price_usd, to_token_price_usd';
    RAISE NOTICE '  - Created materialized view: vw_takers_summary';
    RAISE NOTICE '  - Created performance indexes for taker queries';
END;
$verification$;

COMMIT;