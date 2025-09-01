-- Migrate numeric columns to support human-readable decimals (18 fractional digits)
BEGIN;

-- Takes table: store amounts with 18 decimals
ALTER TABLE takes 
    ALTER COLUMN amount_taken TYPE NUMERIC(78,18) USING amount_taken::numeric,
    ALTER COLUMN amount_paid  TYPE NUMERIC(78,18) USING amount_paid::numeric;

-- Rounds table: support fractional amounts for aggregation
ALTER TABLE rounds 
    ALTER COLUMN initial_available TYPE NUMERIC(78,18) USING initial_available::numeric,
    ALTER COLUMN available_amount TYPE NUMERIC(78,18) USING available_amount::numeric,
    ALTER COLUMN total_volume_sold TYPE NUMERIC(78,18) USING total_volume_sold::numeric;

-- Price history: available amount may be fractional
ALTER TABLE price_history 
    ALTER COLUMN available_amount TYPE NUMERIC(78,18) USING available_amount::numeric;

COMMIT;

