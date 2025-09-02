-- Normalize rounds.transaction_hash to have 0x prefix
UPDATE rounds
SET transaction_hash = '0x' || transaction_hash
WHERE transaction_hash NOT LIKE '0x%';

-- Clamp negative available_amount to zero
UPDATE rounds
SET available_amount = GREATEST(available_amount, 0);

-- Drop is_active column and related index if they exist
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name='rounds' AND column_name='is_active'
  ) THEN
    -- Drop index if present
    PERFORM 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'idx_rounds_active';
    IF FOUND THEN
      EXECUTE 'DROP INDEX IF EXISTS idx_rounds_active';
    END IF;
    -- Drop column
    EXECUTE 'ALTER TABLE rounds DROP COLUMN IF EXISTS is_active';
  END IF;
END$$;

-- Note: active_auction_rounds view not recreated here due to type variance of kicked_at across deployments.
-- It should be updated separately to compute activeness by time instead of is_active.
