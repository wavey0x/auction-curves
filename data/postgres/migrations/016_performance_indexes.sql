-- Migration 016: Performance indexes for faster queries
-- This migration adds indexes on frequently queried columns to improve load times

-- Index for tokens lookups with LOWER() function (expression index)
CREATE INDEX IF NOT EXISTS idx_tokens_lower_address_chain 
    ON tokens(LOWER(address), chain_id);

-- Index for auction and chain combinations
CREATE INDEX IF NOT EXISTS idx_auctions_address_chain 
    ON auctions(auction_address, chain_id);

-- Index for enabled_tokens lookups  
CREATE INDEX IF NOT EXISTS idx_enabled_tokens_auction_chain 
    ON enabled_tokens(auction_address, chain_id);

-- Index for takes queries by auction and timestamp
CREATE INDEX IF NOT EXISTS idx_takes_auction_chain_timestamp 
    ON takes(auction_address, chain_id, timestamp DESC);

-- Index for takes taker counts (if not already exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'idx_takes_taker') THEN
        CREATE INDEX idx_takes_taker ON takes(taker);
    END IF;
END $$;

-- Verification query
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE indexname LIKE 'idx_%' 
    AND schemaname = 'public'
    AND indexname IN (
        'idx_tokens_lower_address_chain',
        'idx_auctions_address_chain', 
        'idx_enabled_tokens_auction_chain',
        'idx_takes_auction_chain_timestamp',
        'idx_takes_taker'
    )
ORDER BY tablename, indexname;