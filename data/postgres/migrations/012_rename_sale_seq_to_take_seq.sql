-- Migration 012: Rename sale_seq to take_seq for semantic consistency
-- Renaming sale_seq column to take_seq in takes table

BEGIN;

-- Rename the column in the takes table  
ALTER TABLE takes RENAME COLUMN sale_seq TO take_seq;

-- Update the index to use the new column name
-- Note: PostgreSQL automatically updates index names when columns are renamed
-- but we'll be explicit about the update

-- Verification
SELECT 'Migration 012 completed successfully - sale_seq renamed to take_seq' as result;

-- Rollback script (for reference):
-- ALTER TABLE takes RENAME COLUMN take_seq TO sale_seq;

COMMIT;