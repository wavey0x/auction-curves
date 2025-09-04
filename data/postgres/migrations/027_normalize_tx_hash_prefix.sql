-- Migration 027: Normalize transaction hash fields to include 0x prefix
-- Ensures that all tx hash columns store a 66-char hex string starting with '0x'

BEGIN;

DO $$
DECLARE
  r RECORD;
  updated_count BIGINT;
BEGIN
  FOR r IN 
    SELECT * FROM (
      VALUES 
        ('rounds', 'transaction_hash'),
        ('takes', 'transaction_hash'),
        ('outbox_events', 'tx_hash'),
        ('enabled_tokens', 'enabled_at_tx_hash')
    ) AS t(table_name, column_name)
  LOOP
    -- Check table and column exist before updating
    IF to_regclass(r.table_name) IS NOT NULL AND EXISTS (
      SELECT 1 FROM information_schema.columns 
      WHERE table_name = r.table_name AND column_name = r.column_name
    ) THEN
      EXECUTE format(
        'UPDATE %I 
           SET %I = ''0x'' || %I
         WHERE %I IS NOT NULL
           AND %I <> ''''
           AND %I NOT LIKE ''0x%%''
           AND length(%I) = 64',
        r.table_name, r.column_name, r.column_name,
        r.column_name, r.column_name, r.column_name, r.column_name
      );
      GET DIAGNOSTICS updated_count = ROW_COUNT;
      RAISE NOTICE 'Updated % rows in %.%', updated_count, r.table_name, r.column_name;
    ELSE
      RAISE NOTICE 'Skipping %.% (table or column not found)', r.table_name, r.column_name;
    END IF;
  END LOOP;
END $$;

-- Verification notices (counts after normalization)
DO $$
DECLARE
  r RECORD;
  remaining BIGINT;
  correct BIGINT;
BEGIN
  FOR r IN 
    SELECT * FROM (
      VALUES 
        ('rounds', 'transaction_hash'),
        ('takes', 'transaction_hash'),
        ('outbox_events', 'tx_hash'),
        ('enabled_tokens', 'enabled_at_tx_hash')
    ) AS t(table_name, column_name)
  LOOP
    IF to_regclass(r.table_name) IS NOT NULL AND EXISTS (
      SELECT 1 FROM information_schema.columns 
      WHERE table_name = r.table_name AND column_name = r.column_name
    ) THEN
      EXECUTE format(
        'SELECT count(*) FROM %I WHERE %I IS NOT NULL AND %I NOT LIKE ''0x%%'' AND length(%I) = 64',
        r.table_name, r.column_name, r.column_name, r.column_name
      ) INTO remaining;

      EXECUTE format(
        'SELECT count(*) FROM %I WHERE %I LIKE ''0x%%'' AND length(%I) = 66',
        r.table_name, r.column_name, r.column_name
      ) INTO correct;

      RAISE NOTICE 'Post-check %.%: % remaining without prefix; % with proper prefix', r.table_name, r.column_name, remaining, correct;
    END IF;
  END LOOP;
END $$;

COMMIT;

