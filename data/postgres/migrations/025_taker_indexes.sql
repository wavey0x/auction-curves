-- Migration 025: Add indexes for taker token pair queries
-- Optimizes performance for taker analytics and token pair frequency analysis

-- Index for taker token pair queries
CREATE INDEX IF NOT EXISTS idx_takes_taker_token_pairs 
ON takes (taker, from_token, to_token);

-- Index for taker timestamps (for activity tracking)
CREATE INDEX IF NOT EXISTS idx_takes_taker_timestamp 
ON takes (taker, timestamp DESC);

-- Index for token pair volume queries
CREATE INDEX IF NOT EXISTS idx_takes_token_pair_volume 
ON takes (from_token, to_token, amount_taken_usd);

-- Composite index for efficient taker takes queries
CREATE INDEX IF NOT EXISTS idx_takes_taker_composite 
ON takes (taker, timestamp DESC, amount_taken_usd);

-- Index for chain-based filtering
CREATE INDEX IF NOT EXISTS idx_takes_taker_chain 
ON takes (taker, chain_id, timestamp DESC);

-- Refresh the materialized view to ensure fresh data
REFRESH MATERIALIZED VIEW CONCURRENTLY vw_takers_summary;