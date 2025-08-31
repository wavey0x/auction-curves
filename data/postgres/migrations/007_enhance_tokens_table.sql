-- Migration 007: Enhance tokens table with comprehensive metadata
-- Add missing fields for complete token information

-- Add new columns for comprehensive token metadata
ALTER TABLE tokens 
ADD COLUMN IF NOT EXISTS category VARCHAR(50),
ADD COLUMN IF NOT EXISTS logo_url VARCHAR(255),
ADD COLUMN IF NOT EXISTS coingecko_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_price_usd DECIMAL(20, 8);

-- Add index for category filtering
CREATE INDEX IF NOT EXISTS idx_tokens_category ON tokens(category);

-- Add index for verification status
CREATE INDEX IF NOT EXISTS idx_tokens_verified ON tokens(is_verified);

-- Update the unique constraint to be more flexible (remove single address constraint)
-- The existing tokens_address_chain_id_key constraint is sufficient for multi-chain
ALTER TABLE tokens DROP CONSTRAINT IF EXISTS tokens_address_key;

-- Add comments for documentation
COMMENT ON COLUMN tokens.category IS 'Token category: stable, crypto, defi, etc.';
COMMENT ON COLUMN tokens.logo_url IS 'URL to token logo image';
COMMENT ON COLUMN tokens.coingecko_id IS 'CoinGecko API ID for price data';
COMMENT ON COLUMN tokens.is_verified IS 'Whether token is verified/trusted';
COMMENT ON COLUMN tokens.last_price_usd IS 'Last cached USD price';