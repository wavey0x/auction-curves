-- Migration 015: Increase transaction_hash column size to handle longer transaction hashes
-- Some networks or processing might produce transaction hashes longer than 100 characters

-- Increase transaction_hash size in rounds table
ALTER TABLE rounds ALTER COLUMN transaction_hash TYPE VARCHAR(200);

-- Increase transaction_hash size in takes table  
ALTER TABLE takes ALTER COLUMN transaction_hash TYPE VARCHAR(200);

-- Add comments for documentation
COMMENT ON COLUMN rounds.transaction_hash IS 'Transaction hash for the kick event (up to 200 chars for various networks)';
COMMENT ON COLUMN takes.transaction_hash IS 'Transaction hash for the take event (up to 200 chars for various networks)';

-- Verification
DO $$
BEGIN
    -- Check if the columns were updated correctly
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'rounds' 
        AND column_name = 'transaction_hash' 
        AND character_maximum_length = 200
    ) THEN
        RAISE EXCEPTION 'rounds.transaction_hash should be VARCHAR(200) after migration';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'takes' 
        AND column_name = 'transaction_hash' 
        AND character_maximum_length = 200
    ) THEN
        RAISE EXCEPTION 'takes.transaction_hash should be VARCHAR(200) after migration';
    END IF;
    
    RAISE NOTICE 'Migration 015 completed successfully: transaction_hash columns increased to 200 characters';
END
$$;