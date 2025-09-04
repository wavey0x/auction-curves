-- Migration 009: Add outbox events table for reliable event publishing
-- Creates the outbox pattern table for Redis Streams integration

BEGIN;

-- Create outbox table for reliable event publishing
CREATE TABLE IF NOT EXISTS outbox_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Event metadata
    type VARCHAR(50) NOT NULL,
    chain_id INTEGER NOT NULL,
    block_number BIGINT NOT NULL,
    tx_hash VARCHAR(100) NOT NULL,
    log_index INTEGER NOT NULL,
    
    -- Event data
    auction_address VARCHAR(100),
    round_id INTEGER,
    from_token VARCHAR(100),
    want_token VARCHAR(100),
    timestamp BIGINT NOT NULL,
    
    -- Payload for event-specific data
    payload_json JSONB NOT NULL DEFAULT '{}',
    
    -- Idempotency and versioning
    uniq VARCHAR(200) NOT NULL,
    ver INTEGER NOT NULL DEFAULT 1,
    
    -- Publishing status
    published_at TIMESTAMPTZ,
    retries INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT outbox_events_uniq_key UNIQUE (uniq)
);

-- Indexes for efficient polling
CREATE INDEX idx_outbox_unpublished ON outbox_events (id) 
    WHERE published_at IS NULL;
CREATE INDEX idx_outbox_chain_block ON outbox_events (chain_id, block_number);
CREATE INDEX idx_outbox_created ON outbox_events (created_at);

-- For monitoring stuck events
CREATE INDEX idx_outbox_retries ON outbox_events (retries) 
    WHERE published_at IS NULL AND retries > 3;

-- Verification
SELECT 'Migration 009 completed successfully' as status;

COMMIT;