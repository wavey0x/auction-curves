-- Ensure uniqueness of takes by (chain_id, transaction_hash, log_index)

-- 1) Deduplicate existing rows, keeping the earliest physical row
DELETE FROM takes a
USING takes b
WHERE a.chain_id = b.chain_id
  AND a.transaction_hash = b.transaction_hash
  AND a.log_index = b.log_index
  AND a.ctid > b.ctid;

-- 2) Add unique index to enforce idempotency going forward
-- For hypertables, unique indexes must include the partitioning key (timestamp)
CREATE UNIQUE INDEX IF NOT EXISTS idx_takes_unique_chain_tx_log_ts
ON takes (chain_id, transaction_hash, log_index, timestamp);
