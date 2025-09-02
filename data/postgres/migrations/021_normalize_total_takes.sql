-- Migration 021: Normalize total_takes column
-- Remove the redundant total_takes column from rounds table and ensure
-- all takes counts are computed dynamically to prevent data inconsistencies

-- Drop the total_takes column from rounds table
ALTER TABLE rounds DROP COLUMN IF EXISTS total_takes;

-- Update the trigger function to remove total_takes references
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the round statistics (removed total_takes increment)
    UPDATE rounds 
    SET 
        total_volume_sold = total_volume_sold + NEW.amount_taken,
        progress_percentage = LEAST(100.0, 
            ((total_volume_sold + NEW.amount_taken) * 100.0) / GREATEST(initial_available, 1)
        ),
        available_amount = GREATEST(0, initial_available - (total_volume_sold + NEW.amount_taken))
    WHERE 
        auction_address = NEW.auction_address 
        AND chain_id = NEW.chain_id 
        AND round_id = NEW.round_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Verify the migration worked
DO $$
DECLARE 
    column_exists boolean;
BEGIN
    -- Check if total_takes column still exists
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'rounds' 
        AND column_name = 'total_takes'
    ) INTO column_exists;
    
    IF column_exists THEN
        RAISE EXCEPTION 'Migration failed: total_takes column still exists in rounds table';
    ELSE
        RAISE NOTICE 'Migration 021 completed successfully: total_takes column removed from rounds table';
        RAISE NOTICE 'All takes counts will now be computed dynamically via JOINs to prevent data inconsistencies';
    END IF;
END $$;