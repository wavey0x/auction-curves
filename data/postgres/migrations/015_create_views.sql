-- Create concise views for rounds and takes with computed is_active and token metadata
BEGIN;

-- vw_rounds: rounds + token metadata + computed status
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
  (GREATEST(0, b.round_end - EXTRACT(EPOCH FROM NOW())::BIGINT)::INTEGER > 0 AND COALESCE(b.available_amount, 0) > 0) AS is_active
FROM base b
LEFT JOIN tokens tf
  ON LOWER(tf.address) = LOWER(b.from_token) AND tf.chain_id = b.chain_id
LEFT JOIN tokens tw
  ON LOWER(tw.address) = LOWER(b.want_token) AND tw.chain_id = b.chain_id;

-- vw_active_rounds: only active rows
CREATE OR REPLACE VIEW vw_active_rounds AS
SELECT *
FROM vw_rounds
WHERE is_active = TRUE
ORDER BY kicked_at DESC;

-- vw_takes: takes with round context and token metadata
CREATE OR REPLACE VIEW vw_takes AS
SELECT 
  als.*, 
  ar.kicked_at AS round_kicked_at,
  -- from token meta
  tf.symbol  AS from_symbol,
  tf.name    AS from_name,
  tf.decimals AS from_decimals,
  -- to (want) token meta
  tw.symbol  AS to_symbol,
  tw.name    AS to_name,
  tw.decimals AS to_decimals
FROM takes als
LEFT JOIN rounds ar
  ON als.auction_address = ar.auction_address
 AND als.chain_id = ar.chain_id
 AND als.round_id = ar.round_id
LEFT JOIN tokens tf
  ON LOWER(tf.address) = LOWER(als.from_token) AND tf.chain_id = als.chain_id
LEFT JOIN tokens tw
  ON LOWER(tw.address) = LOWER(als.to_token) AND tw.chain_id = als.chain_id;

COMMIT;
