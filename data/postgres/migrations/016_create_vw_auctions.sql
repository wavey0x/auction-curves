-- Create vw_auctions view: auctions with want token metadata, latest round snapshot, and enabled from-tokens
BEGIN;

CREATE OR REPLACE VIEW vw_auctions AS
SELECT 
  a.auction_address,
  a.chain_id,
  a.want_token,
  a.update_interval AS price_update_interval,
  a.step_decay_rate,
  a.auction_length,
  a.starting_price,
  a.deployer,
  a.receiver,
  -- Want token metadata
  wt.symbol  AS want_token_symbol,
  wt.name    AS want_token_name,
  wt.decimals AS want_token_decimals,
  -- Latest round snapshot (may be null)
  lr.round_id       AS current_round_id,
  lr.kicked_at      AS last_kicked,
  lr.round_start,
  lr.round_end,
  lr.available_amount AS current_available,
  (lr.round_end IS NOT NULL AND lr.round_end > EXTRACT(EPOCH FROM NOW())::BIGINT AND COALESCE(lr.available_amount,0) > 0) AS has_active_round,
  -- Enabled from-tokens as JSON
  (
    SELECT COALESCE(
      json_agg(
        json_build_object(
          'address', et.token_address,
          'symbol', COALESCE(et_tokens.symbol, 'Unknown'),
          'name', COALESCE(et_tokens.name, 'Unknown'),
          'decimals', COALESCE(et_tokens.decimals, 18),
          'chain_id', et.chain_id
        ) ORDER BY et.enabled_at ASC
      ), '[]'::json
    )
    FROM enabled_tokens et
    LEFT JOIN tokens et_tokens ON LOWER(et.token_address) = LOWER(et_tokens.address) AND et.chain_id = et_tokens.chain_id
    WHERE et.auction_address = a.auction_address AND et.chain_id = a.chain_id
  ) AS from_tokens_json
FROM auctions a
LEFT JOIN LATERAL (
  SELECT r.*
  FROM rounds r
  WHERE r.auction_address = a.auction_address AND r.chain_id = a.chain_id
  ORDER BY r.kicked_at DESC NULLS LAST
  LIMIT 1
) lr ON TRUE
LEFT JOIN tokens wt ON LOWER(a.want_token) = LOWER(wt.address) AND a.chain_id = wt.chain_id;

COMMIT;
