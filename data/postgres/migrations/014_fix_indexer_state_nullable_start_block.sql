-- Migration 014: Fix indexer_state table to allow NULL values for start_block
-- This handles cases where factory addresses are not configured for certain networks

-- Allow NULL values for start_block (will be populated when factory is configured)
ALTER TABLE indexer_state ALTER COLUMN start_block DROP NOT NULL;

-- Add a default value of 0 for start_block 
ALTER TABLE indexer_state ALTER COLUMN start_block SET DEFAULT 0;

-- Add a comment to explain the nullable field
COMMENT ON COLUMN indexer_state.start_block IS 'Starting block for factory indexing (can be NULL if factory not configured yet)';

-- Verification
DO $$
BEGIN
    -- Check if the column is now nullable
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'indexer_state' 
        AND column_name = 'start_block' 
        AND is_nullable = 'NO'
    ) THEN
        RAISE EXCEPTION 'Column start_block should be nullable after migration';
    END IF;
    
    RAISE NOTICE 'Migration 014 completed successfully: start_block is now nullable';
END
$$;