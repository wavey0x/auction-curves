-- Migration 008: Standardize on Unix timestamps
-- Convert kicked_at from timestamp to bigint (Unix timestamp)
-- Use existing timestamp column values which are already correct

BEGIN;

-- Step 1: Verify timestamp column has correct values for all rounds with kicked_at
DO $$
BEGIN
    -- Check if any rounds have kicked_at but no timestamp
    IF EXISTS (
        SELECT 1 FROM rounds 
        WHERE kicked_at IS NOT NULL AND timestamp IS NULL
    ) THEN
        RAISE EXCEPTION 'Found rounds with kicked_at but no timestamp - manual intervention needed';
    END IF;
END
$$;

-- Step 2: Drop dependent views first, then the kicked_at column
DROP VIEW IF EXISTS recent_takes CASCADE;
DROP VIEW IF EXISTS active_auction_rounds CASCADE;

-- Now drop the kicked_at column (timestamp with time zone)
ALTER TABLE rounds DROP COLUMN kicked_at;

-- Step 3: Rename timestamp column to kicked_at (now it's Unix timestamp)
ALTER TABLE rounds RENAME COLUMN timestamp TO kicked_at;

-- Step 4: Make kicked_at NOT NULL since it's a required field
ALTER TABLE rounds ALTER COLUMN kicked_at SET NOT NULL;

-- Step 5: Update indexes that referenced the old kicked_at column
-- Drop old indexes
DROP INDEX IF EXISTS idx_rounds_kicked_at;
DROP INDEX IF EXISTS idx_rounds_active_kicked_at;
DROP INDEX IF EXISTS idx_rounds_timestamp;

-- Create new indexes for the Unix timestamp kicked_at
CREATE INDEX idx_rounds_kicked_at ON rounds(kicked_at);
CREATE INDEX idx_rounds_active_kicked_at ON rounds(kicked_at DESC) WHERE is_active = true;

-- Step 6: Do the same for other tables that might have timestamp columns
-- Check auctions table
DO $$
BEGIN
    -- If auctions table has both discovered_at and timestamp columns, consolidate them
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'auctions' AND column_name = 'discovered_at'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'auctions' AND column_name = 'timestamp'
    ) THEN
        -- Drop discovered_at timestamp column and rename timestamp to discovered_at
        ALTER TABLE auctions DROP COLUMN IF EXISTS discovered_at;
        ALTER TABLE auctions RENAME COLUMN timestamp TO discovered_at;
    END IF;
END
$$;

COMMIT;