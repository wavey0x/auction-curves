-- Change takes.price to human-readable NUMERIC(78,18)
-- If existing data was stored as 1e18-scaled integers, convert by dividing by 1e18
BEGIN;

ALTER TABLE takes
    ALTER COLUMN price TYPE NUMERIC(78,18)
    USING (price::numeric / 1000000000000000000);

COMMIT;

