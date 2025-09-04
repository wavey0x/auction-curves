-- Migration 026: Refactor USD calculations to use views instead of stored columns
-- This migration removes redundant USD columns from takes table and creates
-- comprehensive views for dynamic USD calculations

BEGIN;

-- Drop existing vw_takers_summary materialized view first (it depends on USD columns)
DROP MATERIALIZED VIEW IF EXISTS vw_takers_summary CASCADE;

-- Drop existing redundant indexes first
DROP INDEX IF EXISTS idx_takes_taker_volume;

-- Remove redundant USD columns that are all NULL anyway
ALTER TABLE takes DROP COLUMN IF EXISTS amount_taken_usd CASCADE;
ALTER TABLE takes DROP COLUMN IF EXISTS amount_paid_usd CASCADE;
ALTER TABLE takes DROP COLUMN IF EXISTS from_token_price_usd CASCADE;
ALTER TABLE takes DROP COLUMN IF EXISTS to_token_price_usd CASCADE;

-- Create enhanced takes view with improved price matching logic
DROP VIEW IF EXISTS vw_takes_enriched CASCADE;

CREATE VIEW vw_takes_enriched AS
SELECT 
    t.take_id,
    t.auction_address,
    t.chain_id,
    t.round_id,
    t.take_seq,
    t.taker,
    t.from_token,
    t.to_token,
    t.amount_taken,
    t.amount_paid,
    t.price,
    t.timestamp,
    t.seconds_from_round_start,
    t.block_number,
    t.transaction_hash,
    t.log_index,
    t.gas_price,
    t.base_fee,
    t.priority_fee,
    t.gas_used,
    t.transaction_fee_eth,
    -- Round information
    r.kicked_at as round_kicked_at,
    r.initial_available as round_initial_available,
    -- Token metadata
    tf.symbol as from_token_symbol,
    tf.name as from_token_name,
    tf.decimals as from_token_decimals,
    tt.symbol as to_token_symbol,
    tt.name as to_token_name,
    tt.decimals as to_token_decimals,
    -- Price information with improved fallback logic
    tp_from.price_usd as from_token_price_usd,
    tp_to.price_usd as to_token_price_usd,
    -- Calculated USD values
    CASE 
        WHEN tp_from.price_usd IS NOT NULL THEN t.amount_taken * tp_from.price_usd
        ELSE NULL
    END as amount_taken_usd,
    CASE 
        WHEN tp_to.price_usd IS NOT NULL THEN t.amount_paid * tp_to.price_usd
        ELSE NULL
    END as amount_paid_usd,
    -- Profit/Loss calculations
    CASE 
        WHEN tp_from.price_usd IS NOT NULL AND tp_to.price_usd IS NOT NULL 
        THEN (t.amount_paid * tp_to.price_usd) - (t.amount_taken * tp_from.price_usd)
        ELSE NULL
    END as price_differential_usd,
    CASE 
        WHEN tp_from.price_usd IS NOT NULL AND tp_to.price_usd IS NOT NULL 
             AND (t.amount_taken * tp_from.price_usd) > 0
        THEN ((t.amount_paid * tp_to.price_usd) - (t.amount_taken * tp_from.price_usd)) 
             / (t.amount_taken * tp_from.price_usd) * 100
        ELSE NULL
    END as price_differential_percent,
    -- Transaction fee in USD (for gas analysis)
    CASE 
        WHEN t.transaction_fee_eth IS NOT NULL AND tp_eth.price_usd IS NOT NULL
        THEN t.transaction_fee_eth * tp_eth.price_usd
        ELSE NULL
    END as transaction_fee_usd
FROM takes t
-- Join with rounds for additional context
LEFT JOIN rounds r ON t.auction_address = r.auction_address 
                  AND t.chain_id = r.chain_id 
                  AND t.round_id = r.round_id
-- Join with token metadata
LEFT JOIN tokens tf ON LOWER(tf.address) = LOWER(t.from_token) 
                   AND tf.chain_id = t.chain_id
LEFT JOIN tokens tt ON LOWER(tt.address) = LOWER(t.to_token) 
                   AND tt.chain_id = t.chain_id
-- Advanced price matching: closest block <= take block, fallback to nearest timestamp
LEFT JOIN LATERAL (
    SELECT price_usd
    FROM token_prices tp1
    WHERE tp1.chain_id = t.chain_id 
    AND LOWER(tp1.token_address) = LOWER(t.from_token)
    AND tp1.block_number <= t.block_number
    ORDER BY tp1.block_number DESC, ABS(EXTRACT(EPOCH FROM t.timestamp) - tp1.timestamp) ASC
    LIMIT 1
) tp_from ON true
LEFT JOIN LATERAL (
    SELECT price_usd
    FROM token_prices tp2
    WHERE tp2.chain_id = t.chain_id 
    AND LOWER(tp2.token_address) = LOWER(t.to_token)
    AND tp2.block_number <= t.block_number
    ORDER BY tp2.block_number DESC, ABS(EXTRACT(EPOCH FROM t.timestamp) - tp2.timestamp) ASC
    LIMIT 1
) tp_to ON true
-- Get ETH price for gas fee calculations (assuming WETH or ETH token exists)
LEFT JOIN LATERAL (
    SELECT price_usd
    FROM token_prices tp_eth_inner
    WHERE tp_eth_inner.chain_id = t.chain_id 
    AND (LOWER(tp_eth_inner.token_address) LIKE '%eth%' 
         OR LOWER(tp_eth_inner.token_address) = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2') -- WETH
    AND tp_eth_inner.block_number <= t.block_number
    ORDER BY tp_eth_inner.block_number DESC
    LIMIT 1
) tp_eth ON true;

-- Create optimized materialized view for taker analytics
CREATE MATERIALIZED VIEW mv_takers_summary AS
WITH taker_base_stats AS (
    SELECT 
        t.taker,
        COUNT(*) as total_takes,
        COUNT(DISTINCT t.auction_address) as unique_auctions,
        COUNT(DISTINCT t.chain_id) as unique_chains,
        SUM(t.amount_taken_usd) as total_volume_usd,
        AVG(t.amount_taken_usd) as avg_take_size_usd,
        SUM(t.price_differential_usd) as total_profit_usd,
        AVG(t.price_differential_usd) as avg_profit_per_take_usd,
        MIN(t.timestamp) as first_take,
        MAX(t.timestamp) as last_take,
        ARRAY_AGG(DISTINCT t.chain_id ORDER BY t.chain_id) as active_chains,
        -- Recent activity metrics
        COUNT(*) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '7 days') as takes_last_7d,
        COUNT(*) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '30 days') as takes_last_30d,
        SUM(t.amount_taken_usd) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '7 days') as volume_last_7d,
        SUM(t.amount_taken_usd) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '30 days') as volume_last_30d,
        -- Success rate (positive profit)
        COUNT(*) FILTER (WHERE t.price_differential_usd > 0) as profitable_takes,
        COUNT(*) FILTER (WHERE t.price_differential_usd < 0) as unprofitable_takes
    FROM vw_takes_enriched t
    WHERE t.taker IS NOT NULL
    GROUP BY t.taker
),
ranked_takers AS (
    SELECT 
        *,
        -- Rankings
        RANK() OVER (ORDER BY total_takes DESC) as rank_by_takes,
        RANK() OVER (ORDER BY total_volume_usd DESC NULLS LAST) as rank_by_volume,
        RANK() OVER (ORDER BY total_profit_usd DESC NULLS LAST) as rank_by_profit,
        -- Percentile rankings for better insights
        PERCENT_RANK() OVER (ORDER BY total_takes) as percentile_by_takes,
        PERCENT_RANK() OVER (ORDER BY total_volume_usd NULLS FIRST) as percentile_by_volume,
        -- Success rate calculation
        CASE 
            WHEN (profitable_takes + unprofitable_takes) > 0 
            THEN profitable_takes::DECIMAL / (profitable_takes + unprofitable_takes) * 100
            ELSE NULL
        END as success_rate_percent
    FROM taker_base_stats
)
SELECT * FROM ranked_takers;

-- Create view for taker token pair analytics
CREATE VIEW vw_taker_token_pairs AS
SELECT 
    t.taker,
    t.from_token,
    t.to_token,
    tf.symbol as from_token_symbol,
    tt.symbol as to_token_symbol,
    COUNT(*) as takes_count,
    SUM(t.amount_taken_usd) as total_volume_usd,
    AVG(t.amount_taken_usd) as avg_take_size_usd,
    SUM(t.price_differential_usd) as total_profit_usd,
    AVG(t.price_differential_usd) as avg_profit_per_take_usd,
    MIN(t.timestamp) as first_take_at,
    MAX(t.timestamp) as last_take_at,
    COUNT(DISTINCT t.auction_address) as unique_auctions,
    COUNT(DISTINCT t.chain_id) as unique_chains,
    ARRAY_AGG(DISTINCT t.chain_id ORDER BY t.chain_id) as active_chains,
    -- Success metrics
    COUNT(*) FILTER (WHERE t.price_differential_usd > 0) as profitable_takes,
    CASE 
        WHEN COUNT(*) > 0 
        THEN COUNT(*) FILTER (WHERE t.price_differential_usd > 0)::DECIMAL / COUNT(*) * 100
        ELSE NULL
    END as success_rate_percent
FROM vw_takes_enriched t
LEFT JOIN tokens tf ON LOWER(tf.address) = LOWER(t.from_token) AND tf.chain_id = t.chain_id
LEFT JOIN tokens tt ON LOWER(tt.address) = LOWER(t.to_token) AND tt.chain_id = t.chain_id
WHERE t.taker IS NOT NULL
GROUP BY t.taker, t.from_token, t.to_token, tf.symbol, tt.symbol;

-- Create view for auction-level statistics
CREATE VIEW vw_auction_stats AS
SELECT 
    t.auction_address,
    t.chain_id,
    COUNT(*) as total_takes,
    COUNT(DISTINCT t.taker) as unique_takers,
    COUNT(DISTINCT t.round_id) as total_rounds,
    SUM(t.amount_taken_usd) as total_volume_usd,
    AVG(t.amount_taken_usd) as avg_take_size_usd,
    SUM(t.price_differential_usd) as total_arbitrage_profit_usd,
    MIN(t.timestamp) as first_activity,
    MAX(t.timestamp) as last_activity,
    -- Token pair diversity
    COUNT(DISTINCT CONCAT(t.from_token, '-', t.to_token)) as unique_token_pairs,
    -- Recent activity
    COUNT(*) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '7 days') as takes_last_7d,
    COUNT(*) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '30 days') as takes_last_30d,
    SUM(t.amount_taken_usd) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '7 days') as volume_last_7d,
    SUM(t.amount_taken_usd) FILTER (WHERE t.timestamp >= NOW() - INTERVAL '30 days') as volume_last_30d
FROM vw_takes_enriched t
WHERE t.auction_address IS NOT NULL
GROUP BY t.auction_address, t.chain_id;

-- Create indexes for performance optimization
CREATE UNIQUE INDEX idx_mv_takers_summary_taker ON mv_takers_summary(taker);
CREATE INDEX idx_mv_takers_summary_volume ON mv_takers_summary(total_volume_usd DESC NULLS LAST);
CREATE INDEX idx_mv_takers_summary_takes ON mv_takers_summary(total_takes DESC);
CREATE INDEX idx_mv_takers_summary_profit ON mv_takers_summary(total_profit_usd DESC NULLS LAST);
CREATE INDEX idx_mv_takers_summary_recent ON mv_takers_summary(last_take DESC NULLS LAST);

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_taker_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_takers_summary;
    RAISE NOTICE 'Refreshed mv_takers_summary materialized view';
END;
$$ LANGUAGE plpgsql;

-- Add helpful comments
COMMENT ON VIEW vw_takes_enriched IS 'Enhanced takes view with dynamic USD calculations, profit/loss metrics, and comprehensive token/round context';
COMMENT ON MATERIALIZED VIEW mv_takers_summary IS 'Pre-calculated taker statistics with rankings, recent activity metrics, and success rates. Refreshed hourly.';
COMMENT ON VIEW vw_taker_token_pairs IS 'Taker activity aggregated by token pairs for analyzing trading preferences and success rates';
COMMENT ON VIEW vw_auction_stats IS 'Auction-level aggregated statistics including taker diversity, volume, and activity metrics';

-- Verification
DO $verification$
DECLARE
    takes_count INTEGER;
    enriched_count INTEGER;
    takers_count INTEGER;
    mv_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO takes_count FROM takes;
    SELECT COUNT(*) INTO enriched_count FROM vw_takes_enriched WHERE amount_taken_usd IS NOT NULL;
    SELECT COUNT(DISTINCT taker) INTO takers_count FROM takes WHERE taker IS NOT NULL;
    SELECT COUNT(*) INTO mv_count FROM mv_takers_summary;
    
    RAISE NOTICE 'Migration 026 completed successfully:';
    RAISE NOTICE '  - Total takes: %', takes_count;
    RAISE NOTICE '  - Takes with USD values: %', enriched_count;
    RAISE NOTICE '  - Unique takers: %', takers_count;
    RAISE NOTICE '  - Takers in summary: %', mv_count;
    RAISE NOTICE '  - Removed NULL USD columns from takes table';
    RAISE NOTICE '  - Created vw_takes_enriched with dynamic USD calculations';
    RAISE NOTICE '  - Created mv_takers_summary materialized view';
    RAISE NOTICE '  - Created vw_taker_token_pairs for pair analytics';
    RAISE NOTICE '  - Created vw_auction_stats for auction metrics';
    RAISE NOTICE '  - Added performance indexes and refresh function';
END;
$verification$;

COMMIT;