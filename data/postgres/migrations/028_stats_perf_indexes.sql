-- Migration 028: Add performance indexes supporting /system/stats

BEGIN;

-- Speeds up active_auctions: rounds with available tokens, grouped by auction
CREATE INDEX IF NOT EXISTS idx_rounds_auction_chain_available_pos
  ON rounds (auction_address, chain_id)
  WHERE available_amount > 0;

-- Helps join/filter on takes by auction and chain
CREATE INDEX IF NOT EXISTS idx_takes_auction_chain
  ON takes (auction_address, chain_id);

-- Helps distinct token(address) per chain
CREATE INDEX IF NOT EXISTS idx_tokens_chain_address
  ON tokens (chain_id, address);

-- Optional: ensure views exist is not handled here; this migration is safe to run regardless

COMMIT;

