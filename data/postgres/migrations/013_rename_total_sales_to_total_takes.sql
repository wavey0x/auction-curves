-- Migration 013: Rename total_sales to total_takes in rounds table
-- Eliminating all "sales" terminology in favor of "takes"

BEGIN;

-- Rename the column in the rounds table
ALTER TABLE rounds RENAME COLUMN total_sales TO total_takes;

-- Update the trigger function to use the new column name
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the round statistics when a take is inserted
    UPDATE rounds SET
        total_takes = total_takes + 1,
        available_amount = GREATEST(available_amount - NEW.amount_taken, 0)
    WHERE auction_address = NEW.auction_address
      AND chain_id = NEW.chain_id
      AND round_id = NEW.round_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Verification
SELECT 'Migration 013 completed successfully - total_sales renamed to total_takes' as result;

-- Rollback script (for reference):
-- ALTER TABLE rounds RENAME COLUMN total_takes TO total_sales;
-- (and update trigger function back)

COMMIT;