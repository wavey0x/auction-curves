-- Store price as human-readable want-per-from with 18 decimals
BEGIN;

ALTER TABLE takes 
    ALTER COLUMN price TYPE NUMERIC(78,18) USING price::numeric / 1e18;

COMMIT;

