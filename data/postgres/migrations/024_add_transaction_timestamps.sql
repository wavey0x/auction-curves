-- Migration 024: Add transaction timestamps to price_requests and token_prices
-- This enables time-based processing where quote APIs only process recent transactions

BEGIN;

-- Add transaction timestamp to price_requests table
-- This stores the exact timestamp from the blockchain transaction (kick/take)
ALTER TABLE price_requests ADD COLUMN IF NOT EXISTS txn_timestamp BIGINT;

-- Add price source specification to allow targeted processing
ALTER TABLE price_requests ADD COLUMN IF NOT EXISTS price_source VARCHAR(50) DEFAULT 'all';

-- Add transaction timestamp to token_prices table  
-- This preserves the original transaction timing for analytics and traceability
ALTER TABLE token_prices ADD COLUMN IF NOT EXISTS txn_timestamp BIGINT;

-- Add indexes for efficient timestamp-based queries
CREATE INDEX IF NOT EXISTS idx_price_requests_txn_timestamp ON price_requests(txn_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_token_prices_txn_timestamp ON token_prices(txn_timestamp DESC);

-- Add index for price source filtering
CREATE INDEX IF NOT EXISTS idx_price_requests_price_source ON price_requests(price_source);

-- Add comments to document the new fields
COMMENT ON COLUMN price_requests.txn_timestamp IS 'Unix timestamp from the originating blockchain transaction (kick/take)';
COMMENT ON COLUMN price_requests.price_source IS 'Intended price service(s): all, ypm, odos, enso, or comma-separated list';
COMMENT ON COLUMN token_prices.txn_timestamp IS 'Unix timestamp from the blockchain transaction that generated this price request';

-- Update existing price_requests to have price_source = 'all' (already defaulted above)
-- Update existing token_prices to inherit txn_timestamp from their corresponding price_requests
UPDATE token_prices 
SET txn_timestamp = (
    SELECT EXTRACT(EPOCH FROM pr.created_at)::BIGINT  -- Convert timestamp to unix epoch
    FROM price_requests pr 
    WHERE pr.chain_id = token_prices.chain_id 
      AND pr.block_number = token_prices.block_number 
      AND pr.token_address = token_prices.token_address
    LIMIT 1
)
WHERE txn_timestamp IS NULL;

-- For token_prices without corresponding price_requests, use their own created_at timestamp
-- This handles prices created by the automatic ETH pricing system
UPDATE token_prices 
SET txn_timestamp = EXTRACT(EPOCH FROM created_at)::BIGINT
WHERE txn_timestamp IS NULL;

-- Verification: Check that indexes were created
DO $$
BEGIN
    -- Test that we can query by transaction timestamp efficiently
    PERFORM * FROM price_requests WHERE txn_timestamp > 0 LIMIT 1;
    PERFORM * FROM token_prices WHERE txn_timestamp > 0 LIMIT 1;
    
    RAISE NOTICE '✅ Transaction timestamp migration completed successfully';
    RAISE NOTICE '   • Added txn_timestamp to price_requests and token_prices';
    RAISE NOTICE '   • Added price_source to price_requests';
    RAISE NOTICE '   • Created performance indexes';
    RAISE NOTICE '   • Populated existing records with fallback timestamps';
END $$;

COMMIT;