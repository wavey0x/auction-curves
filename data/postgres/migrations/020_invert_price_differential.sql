-- Migration 020: Invert price differential to show auction perspective
-- From: positive = taker profit, negative = taker loss  
-- To: positive = auction profit, negative = auction loss

BEGIN;

-- Drop the existing view
DROP VIEW IF EXISTS vw_takes_with_prices;

-- Recreate the view with inverted price differential calculation
CREATE VIEW vw_takes_with_prices AS
SELECT 
  als.*,
  -- Token information
  tf.symbol AS from_token_symbol,
  tf.name AS from_token_name,
  tf.decimals AS from_token_decimals,
  tw.symbol AS want_token_symbol,
  tw.name AS want_token_name,
  tw.decimals AS want_token_decimals,
  -- Price information
  tp_from.price_usd AS from_token_price_usd,
  tp_want.price_usd AS want_token_price_usd,
  -- USD calculations
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
  ON als.from_token = tf.address
 AND als.chain_id = tf.chain_id
LEFT JOIN tokens tw
  ON ar.auction_address IN (
    SELECT auction_address 
    FROM auctions a 
    WHERE a.want_token = tw.address 
      AND a.chain_id = tw.chain_id
      AND a.auction_address = ar.auction_address
      AND a.chain_id = ar.chain_id
  )
LEFT JOIN token_prices tp_from
  ON als.from_token = tp_from.token_address
 AND als.chain_id = tp_from.chain_id
 AND als.block_number = tp_from.block_number
LEFT JOIN token_prices tp_want
  ON tw.address = tp_want.token_address
 AND als.chain_id = tp_want.chain_id  
 AND als.block_number = tp_want.block_number;

-- Verify the view was created successfully
SELECT COUNT(*) as view_row_count FROM vw_takes_with_prices LIMIT 1;

COMMIT;

-- Rollback instructions:
-- To revert this change:
-- 1. Run migration 019 again to restore the original taker perspective calculation