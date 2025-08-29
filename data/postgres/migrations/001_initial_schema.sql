-- Migration 001: Initial Schema
-- This migration sets up the complete auction house database schema

\echo 'Running migration 001: Initial Schema'

-- Check if we're running on the correct database
SELECT current_database();

-- Run the main schema
\i ../schema.sql

-- Insert some initial data
INSERT INTO tokens (address, symbol, name, decimals) VALUES
('0x0000000000000000000000000000000000000000', 'ETH', 'Ethereum', 18),
('0xA0b86a33E6441b8C87C83e4F8E3FBcE66A6F8cDf', 'USDC', 'USD Coin', 6),
('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'WETH', 'Wrapped Ether', 18);

\echo 'Migration 001 completed successfully'