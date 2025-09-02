-- Migration 022: Add Gas Tracking to Takes Table
-- Adds gas price, base fee, priority fee, gas used, and total transaction fee to takes

BEGIN;

-- Add gas tracking columns to takes table
ALTER TABLE takes ADD COLUMN IF NOT EXISTS gas_price NUMERIC(20,9);        -- Gas price in Gwei (human readable)
ALTER TABLE takes ADD COLUMN IF NOT EXISTS base_fee NUMERIC(20,9);         -- Base fee in Gwei (human readable)  
ALTER TABLE takes ADD COLUMN IF NOT EXISTS priority_fee NUMERIC(20,9);     -- Priority fee in Gwei (0 for legacy txns)
ALTER TABLE takes ADD COLUMN IF NOT EXISTS gas_used NUMERIC(20,0);         -- Total gas used by the transaction
ALTER TABLE takes ADD COLUMN IF NOT EXISTS transaction_fee_eth NUMERIC(20,18); -- Total fee paid in ETH (human readable)

-- Add comments to document the fields
COMMENT ON COLUMN takes.gas_price IS 'Gas price in Gwei (human readable)';
COMMENT ON COLUMN takes.base_fee IS 'Base fee in Gwei (human readable, from EIP-1559)';
COMMENT ON COLUMN takes.priority_fee IS 'Priority fee in Gwei (0 for legacy transactions)';
COMMENT ON COLUMN takes.gas_used IS 'Total gas used by the transaction';
COMMENT ON COLUMN takes.transaction_fee_eth IS 'Total transaction fee paid in ETH (human readable)';

-- Create index on gas tracking fields for analysis queries
CREATE INDEX IF NOT EXISTS idx_takes_gas_price ON takes (gas_price);
CREATE INDEX IF NOT EXISTS idx_takes_transaction_fee ON takes (transaction_fee_eth);
CREATE INDEX IF NOT EXISTS idx_takes_timestamp_fee ON takes (timestamp, transaction_fee_eth);

-- Verification: Check that columns were added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'takes' 
        AND column_name IN ('gas_price', 'base_fee', 'priority_fee', 'gas_used', 'transaction_fee_eth')
    ) THEN
        RAISE NOTICE '✅ Gas tracking columns added successfully to takes table';
    ELSE
        RAISE EXCEPTION '❌ Failed to add gas tracking columns to takes table';
    END IF;
END $$;

COMMIT;