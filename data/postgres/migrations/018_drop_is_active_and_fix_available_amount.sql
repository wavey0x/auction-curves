-- Migration 018: Drop is_active column and ensure accurate available_amount tracking
-- is_active is now calculated dynamically based on time_remaining > 0 AND available_amount > 0

-- Drop the is_active column from rounds table
ALTER TABLE rounds DROP COLUMN IF EXISTS is_active;

-- Update table comment to reflect the change
COMMENT ON TABLE rounds IS 'Tracks individual rounds within Auctions, created by kick events. is_active is calculated dynamically based on round_end and available_amount.';

-- Add comment about available_amount accuracy
COMMENT ON COLUMN rounds.available_amount IS 'Remaining tokens available for taking, updated by indexer from blockchain state after each take';

-- Note: The indexer will be enhanced to call auction.available(from_token) after each take
-- to ensure available_amount reflects the true blockchain state