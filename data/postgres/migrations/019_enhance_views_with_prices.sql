-- Migration 019: Enhance existing views with USD price data
-- Adds token_prices integration to vw_takes and vw_rounds views

BEGIN;

-- Drop existing views to recreate with price data
DROP VIEW IF EXISTS vw_takes;
DROP VIEW IF EXISTS vw_active_rounds;
DROP VIEW IF EXISTS vw_rounds;

-- Recreate vw_rounds with price data support
CREATE OR REPLACE VIEW vw_rounds AS
WITH base AS (
  SELECT 
    ar.auction_address,
    ar.chain_id,
    ar.round_id,
    ar.from_token,
    ar.kicked_at,
    ar.initial_available,
    ar.available_amount,
    ar.total_takes,
    ar.total_volume_sold,
    ar.block_number,
    ar.transaction_hash,
    ahp.want_token,
    ahp.auction_length,
    ar.round_end
  FROM rounds ar
  JOIN auctions ahp
    ON ar.auction_address = ahp.auction_address
   AND ar.chain_id = ahp.chain_id
)
SELECT 
  b.auction_address,
  b.chain_id,
  b.round_id,
  b.from_token,
  b.kicked_at,
  b.initial_available,
  b.available_amount,
  b.total_takes,
  b.total_volume_sold,
  b.block_number,
  b.transaction_hash,
  b.want_token,
  b.auction_length,
  -- from_token metadata
  tf.symbol  AS from_symbol,
  tf.name    AS from_name,
  tf.decimals AS from_decimals,
  -- want_token metadata
  tw.symbol  AS want_symbol,
  tw.name    AS want_name,
  tw.decimals AS want_decimals,
  -- computed fields
  GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER AS time_remaining,
  GREATEST(0, b.auction_length - GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER)::INTEGER AS seconds_elapsed,
  (GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER > 0 AND COALESCE(b.available_amount, 0) > 0) AS is_active,
  -- USD price data at kick block
  tp_from.price_usd AS from_token_price_usd,
  tp_want.price_usd AS want_token_price_usd
FROM base b
LEFT JOIN tokens tf
  ON LOWER(tf.address) = LOWER(b.from_token) AND tf.chain_id = b.chain_id
LEFT JOIN tokens tw
  ON LOWER(tw.address) = LOWER(b.want_token) AND tw.chain_id = b.chain_id
-- Join with token_prices for from_token at kick block
LEFT JOIN token_prices tp_from 
  ON LOWER(tp_from.token_address) = LOWER(b.from_token)
  AND tp_from.chain_id = b.chain_id
  AND tp_from.block_number = b.block_number
  AND tp_from.source = 'ypricemagic'
-- Join with token_prices for want_token at kick block  
LEFT JOIN token_prices tp_want 
  ON LOWER(tp_want.token_address) = LOWER(b.want_token)
  AND tp_want.chain_id = b.chain_id
  AND tp_want.block_number = b.block_number
  AND tp_want.source = 'ypricemagic';

-- Recreate vw_active_rounds view
CREATE OR REPLACE VIEW vw_active_rounds AS
SELECT *
FROM vw_rounds
WHERE is_active = TRUE
ORDER BY kicked_at DESC;

-- Recreate vw_takes with USD price data
CREATE OR REPLACE VIEW vw_takes AS
SELECT 
  als.*,
  ar.kicked_at AS round_kicked_at,
  -- from token metadata
  tf.symbol  AS from_symbol,
  tf.name    AS from_name,
  tf.decimals AS from_decimals,
  -- to (want) token metadata
  tw.symbol  AS to_symbol,
  tw.name    AS to_name,
  tw.decimals AS to_decimals,
  -- USD price data at take block
  tp_from.price_usd AS from_token_price_usd,
  tp_want.price_usd AS want_token_price_usd,
  -- Calculate USD values
  CASE 
    WHEN tp_from.price_usd IS NOT NULL THEN
      (als.amount_taken * tp_from.price_usd)
    ELSE NULL
  END AS amount_taken_usd,
  CASE 
    WHEN tp_want.price_usd IS NOT NULL THEN
      (als.amount_paid * tp_want.price_usd)
    ELSE NULL
  END AS amount_paid_usd,
  -- Calculate differential from auction perspective (amount paid - value given away)
  CASE 
    WHEN tp_from.price_usd IS NOT NULL AND tp_want.price_usd IS NOT NULL THEN
      (als.amount_paid * tp_want.price_usd) - (als.amount_taken * tp_from.price_usd)
    ELSE NULL
  END AS price_differential_usd,
  -- Calculate percentage differential from auction perspective
  CASE 
    WHEN tp_from.price_usd IS NOT NULL AND tp_want.price_usd IS NOT NULL 
         AND (als.amount_taken * tp_from.price_usd) > 0 THEN
      ((als.amount_paid * tp_want.price_usd) - (als.amount_taken * tp_from.price_usd)) 
      / (als.amount_taken * tp_from.price_usd) * 100
    ELSE NULL
  END AS price_differential_percent
FROM takes als
LEFT JOIN rounds ar
  ON als.auction_address = ar.auction_address
 AND als.chain_id = ar.chain_id
 AND als.round_id = ar.round_id
LEFT JOIN tokens tf
  ON LOWER(tf.address) = LOWER(als.from_token) AND tf.chain_id = als.chain_id
LEFT JOIN tokens tw
  ON LOWER(tw.address) = LOWER(als.to_token) AND tw.chain_id = als.chain_id
-- Join with token_prices for from_token at take block
LEFT JOIN token_prices tp_from 
  ON LOWER(tp_from.token_address) = LOWER(als.from_token)
  AND tp_from.chain_id = als.chain_id
  AND tp_from.block_number = als.block_number
  AND tp_from.source = 'ypricemagic'
-- Join with token_prices for want_token at take block
-- Note: using auctions table to get want_token since takes.to_token is the want_token
LEFT JOIN token_prices tp_want 
  ON LOWER(tp_want.token_address) = LOWER(als.to_token)
  AND tp_want.chain_id = als.chain_id
  AND tp_want.block_number = als.block_number
  AND tp_want.source = 'ypricemagic';

-- Verify views were created successfully
SELECT 
  schemaname, 
  viewname, 
  definition IS NOT NULL as has_definition
FROM pg_views 
WHERE viewname IN ('vw_rounds', 'vw_active_rounds', 'vw_takes')
ORDER BY viewname;

COMMIT;