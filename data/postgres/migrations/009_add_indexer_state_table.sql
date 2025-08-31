-- Migration 009: Add indexer_state table for tracking blockchain processing progress
-- This table is essential for the custom Web3.py indexer to track which blocks have been processed

-- Create indexer_state table if it doesn't exist
CREATE TABLE IF NOT EXISTS indexer_state (
    chain_id INTEGER PRIMARY KEY,
    last_indexed_block INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_indexer_state_updated ON indexer_state (updated_at);

-- Add a comment for documentation
COMMENT ON TABLE indexer_state IS 'Tracks blockchain indexer progress per chain to prevent duplicate event processing';
COMMENT ON COLUMN indexer_state.chain_id IS 'Blockchain network identifier (1=Ethereum, 31337=Anvil, etc.)';
COMMENT ON COLUMN indexer_state.last_indexed_block IS 'Last block number that was successfully processed by the indexer';
COMMENT ON COLUMN indexer_state.updated_at IS 'Timestamp of last indexer update for monitoring';

-- Verification
DO $$
BEGIN
    -- Check if table exists
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'indexer_state') THEN
        RAISE EXCEPTION 'Table indexer_state was not created successfully';
    END IF;
    
    RAISE NOTICE 'Migration 009 completed successfully: indexer_state table ready for blockchain event indexing';
END
$$;