-- Migration 011: Rename sale_id to take_id for consistency
-- Renaming sale_id column to take_id in takes table for better semantic clarity

BEGIN;

-- Rename the column in the takes table
ALTER TABLE takes RENAME COLUMN sale_id TO take_id;

-- Drop the old primary key constraint if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'takes_pkey' 
        AND table_name = 'takes'
    ) THEN
        ALTER TABLE takes DROP CONSTRAINT takes_pkey;
    END IF;
END $$;

-- Recreate the primary key with the new column name
ALTER TABLE takes ADD PRIMARY KEY (take_id, timestamp);

-- Verification
SELECT 'Migration 011 completed successfully - sale_id renamed to take_id' as result;

-- Rollback script (for reference):
-- ALTER TABLE takes RENAME COLUMN take_id TO sale_id;
-- ALTER TABLE takes DROP CONSTRAINT takes_pkey;
-- ALTER TABLE takes ADD PRIMARY KEY (sale_id, timestamp);

COMMIT;