-- Migration 023: Remove restrictive constraints from price_requests table
-- Allows flexible request_type values including 'backfill'

BEGIN;

-- Remove the restrictive request_type constraint
ALTER TABLE price_requests DROP CONSTRAINT IF EXISTS price_requests_request_type_check;

-- Remove the restrictive status constraint (make it more flexible)
ALTER TABLE price_requests DROP CONSTRAINT IF EXISTS price_requests_status_check;

-- Add more flexible constraints
ALTER TABLE price_requests ADD CONSTRAINT price_requests_request_type_check 
    CHECK (request_type IS NOT NULL AND LENGTH(request_type) > 0);

ALTER TABLE price_requests ADD CONSTRAINT price_requests_status_check 
    CHECK (status IS NOT NULL AND LENGTH(status) > 0);

-- Add comments to document the flexible approach
COMMENT ON COLUMN price_requests.request_type IS 'Request type: kick, take, backfill, manual, etc.';
COMMENT ON COLUMN price_requests.status IS 'Status: pending, processing, completed, failed, etc.';

-- Verification: Check that constraints were updated
DO $$
BEGIN
    -- Test that we can now use 'backfill' as request_type
    INSERT INTO price_requests (
        chain_id, block_number, token_address, request_type, status
    ) VALUES (
        999, 999999, '0x0000000000000000000000000000000000000000', 'backfill', 'test'
    );
    
    -- Clean up test data
    DELETE FROM price_requests WHERE chain_id = 999 AND block_number = 999999;
    
    RAISE NOTICE '✅ Constraint removal successful - flexible request_type and status now allowed';
END $$;

COMMIT;