-- Drop unused price_history table if it exists
BEGIN;

DROP VIEW IF EXISTS vw_price_history CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;

COMMIT;

