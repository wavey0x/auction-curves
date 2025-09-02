-- Migration 016: Add price request queue and token price tables
-- Creates infrastructure for ypricemagic integration with multi-source support

BEGIN;

-- Queue for price lookup requests
CREATE TABLE price_requests (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL,
    block_number BIGINT NOT NULL,
    token_address VARCHAR(100) NOT NULL,
    request_type VARCHAR(20) NOT NULL CHECK (request_type IN ('kick', 'take')),
    auction_address VARCHAR(100),
    round_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    -- Prevent duplicate requests for same token at same block
    UNIQUE(chain_id, block_number, token_address)
);

-- Token price history with multi-source support
CREATE TABLE token_prices (
    id SERIAL PRIMARY KEY,
    chain_id INTEGER NOT NULL,
    block_number BIGINT NOT NULL,
    token_address VARCHAR(100) NOT NULL,
    price_usd NUMERIC(40, 18) NOT NULL,
    timestamp BIGINT NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'ypricemagic',
    created_at TIMESTAMP DEFAULT NOW(),
    -- Allow multiple sources for same token/block combination
    UNIQUE(chain_id, block_number, token_address, source)
);

-- Indexes for performance
CREATE INDEX idx_price_requests_status ON price_requests(status);
CREATE INDEX idx_price_requests_created ON price_requests(created_at DESC);
CREATE INDEX idx_price_requests_chain_token ON price_requests(chain_id, token_address);

CREATE INDEX idx_token_prices_lookup ON token_prices(chain_id, token_address, block_number DESC);
CREATE INDEX idx_token_prices_source ON token_prices(source);
CREATE INDEX idx_token_prices_timestamp ON token_prices(timestamp DESC);
CREATE INDEX idx_token_prices_chain_block ON token_prices(chain_id, block_number DESC);

-- Comments for documentation
COMMENT ON TABLE price_requests IS 'Queue for token price lookup requests from auction events';
COMMENT ON TABLE token_prices IS 'Historical token prices in USD from various sources';

COMMENT ON COLUMN price_requests.request_type IS 'Type of auction event that triggered the request: kick or take';
COMMENT ON COLUMN price_requests.retry_count IS 'Number of retry attempts for failed requests';
COMMENT ON COLUMN token_prices.source IS 'Price data source: ypricemagic, chainlink, coingecko, etc.';
COMMENT ON COLUMN token_prices.price_usd IS 'Token price in USD with high precision';

-- Verification: Check tables were created
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('price_requests', 'token_prices');

-- Verification: Check indexes were created
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE tablename IN ('price_requests', 'token_prices');

COMMIT;