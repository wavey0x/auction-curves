-- Auction Database Schema
-- This schema supports the Auction → AuctionRound → AuctionSale structure
-- Works WITH Rindexer's automatic table generation for blockchain events

-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- TOKEN METADATA CACHE
-- ============================================================================
-- Simple token info cache (since Rindexer focuses on events, not token metadata)
CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) UNIQUE NOT NULL,
    symbol VARCHAR(20),
    name VARCHAR(100),
    decimals INTEGER,
    chain_id INTEGER NOT NULL DEFAULT 1,
    
    -- Metadata
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (address, chain_id)
);

-- Create indexes for tokens table
CREATE INDEX idx_tokens_address ON tokens (address);
CREATE INDEX idx_tokens_chain_id ON tokens (chain_id);

-- ============================================================================
-- AUCTION PARAMETERS CACHE
-- ============================================================================
-- Cache for Auction contract parameters (supplements Rindexer event data)
-- This is useful since parameters are immutable and not emitted in every event
CREATE TABLE auction_parameters (
    auction_address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    
    -- Auction parameters (renamed from ParameterizedAuction)
    price_update_interval INTEGER NOT NULL,
    step_decay DECIMAL(30,0) NOT NULL, -- RAY precision - DEPRECATED, use step_decay_rate
    step_decay_rate DECIMAL(30,0), -- New field: decay rate per 36-second step (e.g., 0.995 * 1e27)
    fixed_starting_price DECIMAL(30,0), -- NULL if dynamic
    auction_length INTEGER, -- seconds - now AUCTION_LENGTH constant
    starting_price DECIMAL(30,0), -- dynamic pricing value
    
    -- Token addresses
    want_token VARCHAR(42),
    
    -- Governance info
    deployer VARCHAR(42),
    receiver VARCHAR(42),
    governance VARCHAR(42),
    
    -- Discovery metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    factory_address VARCHAR(42),
    auction_version VARCHAR(10) DEFAULT '0.1.0', -- Contract version: 0.0.1 (legacy) or 0.1.0 (new)
    
    -- Derived fields for UI
    decay_rate_percent DECIMAL(10,4), -- Calculated decay rate as percentage
    update_interval_minutes DECIMAL(10,2), -- Update interval in minutes
    
    PRIMARY KEY (auction_address, chain_id)
);

-- Create indexes for auction_parameters table
CREATE INDEX idx_auction_params_deployer ON auction_parameters (deployer);
CREATE INDEX idx_auction_params_factory ON auction_parameters (factory_address);
CREATE INDEX idx_auction_params_chain ON auction_parameters (chain_id);

-- ============================================================================
-- AUCTION ROUND TRACKING
-- ============================================================================
-- Track rounds within each Auction (supplements Rindexer kick events)
-- Each kick creates a new round with incremental round_id per Auction
CREATE TABLE auction_rounds (
    auction_address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    round_id INTEGER NOT NULL, -- Incremental per Auction: 1, 2, 3...
    from_token VARCHAR(42) NOT NULL,
    
    -- Round data
    kicked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_available DECIMAL(30,0) NOT NULL, -- Initial tokens for this round
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Current state (updated as round progresses)
    current_price DECIMAL(30,0), -- Current calculated price
    available_amount DECIMAL(30,0), -- Remaining tokens
    time_remaining INTEGER, -- Seconds until round ends
    seconds_elapsed INTEGER DEFAULT 0, -- Seconds since round started
    
    -- Round statistics
    total_sales INTEGER DEFAULT 0,
    total_volume_sold DECIMAL(30,0) DEFAULT 0,
    progress_percentage DECIMAL(5,2) DEFAULT 0, -- 0-100%
    
    -- Block data
    block_number BIGINT NOT NULL,
    transaction_hash VARCHAR(66) NOT NULL,
    
    PRIMARY KEY (auction_address, chain_id, round_id),
    FOREIGN KEY (auction_address, chain_id) REFERENCES auction_parameters(auction_address, chain_id)
);

-- Create indexes for auction_rounds table
CREATE INDEX idx_auction_rounds_active ON auction_rounds (is_active);
CREATE INDEX idx_auction_rounds_kicked_at ON auction_rounds (kicked_at);
CREATE INDEX idx_auction_rounds_chain ON auction_rounds (chain_id);
CREATE INDEX idx_auction_rounds_from_token ON auction_rounds (from_token);

-- Note: auction_rounds is NOT a hypertable to allow foreign key references from hypertables

-- ============================================================================
-- AUCTION SALES TRACKING
-- ============================================================================
-- Track individual sales within rounds (supplements Rindexer take events)
-- Each take/sale gets a sequence number within the round
CREATE TABLE auction_sales (
    sale_id VARCHAR(100), -- Format: {auction}-{roundId}-{saleSeq}
    auction_address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    round_id INTEGER NOT NULL,
    sale_seq INTEGER NOT NULL, -- Sequence within round: 1, 2, 3...
    
    -- Sale data
    taker VARCHAR(42) NOT NULL,
    from_token VARCHAR(42) NOT NULL,
    to_token VARCHAR(42) NOT NULL, -- want_token
    amount_taken DECIMAL(30,0) NOT NULL, -- Amount of from_token purchased
    amount_paid DECIMAL(30,0) NOT NULL, -- Amount of to_token paid
    price DECIMAL(30,0) NOT NULL, -- Price per from_token at time of sale
    
    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    seconds_from_round_start INTEGER NOT NULL,
    
    -- Block data
    block_number BIGINT NOT NULL,
    transaction_hash VARCHAR(66) NOT NULL,
    log_index INTEGER NOT NULL,
    
    PRIMARY KEY (sale_id, timestamp),
    FOREIGN KEY (auction_address, chain_id, round_id) REFERENCES auction_rounds(auction_address, chain_id, round_id)
);

-- Create indexes for auction_sales table
CREATE INDEX idx_auction_sales_timestamp ON auction_sales (timestamp);
CREATE INDEX idx_auction_sales_chain ON auction_sales (chain_id);
CREATE INDEX idx_auction_sales_round ON auction_sales (auction_address, chain_id, round_id);
CREATE INDEX idx_auction_sales_taker ON auction_sales (taker);
CREATE INDEX idx_auction_sales_tx_hash ON auction_sales (transaction_hash);

-- Make auction_sales a hypertable for time-series optimization
SELECT create_hypertable('auction_sales', 'timestamp', if_not_exists => TRUE);

-- ============================================================================
-- PRICE HISTORY TRACKING
-- ============================================================================
-- Track price changes over time for each round (for charting)
CREATE TABLE price_history (
    auction_address VARCHAR(42) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    round_id INTEGER NOT NULL,
    from_token VARCHAR(42) NOT NULL,
    
    -- Price data
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(30,0) NOT NULL,
    available_amount DECIMAL(30,0) NOT NULL,
    seconds_from_round_start INTEGER NOT NULL,
    
    -- Block context
    block_number BIGINT NOT NULL,
    
    FOREIGN KEY (auction_address, chain_id, round_id) REFERENCES auction_rounds(auction_address, chain_id, round_id)
);

-- Create indexes for price_history table
CREATE INDEX idx_price_history_timestamp ON price_history (timestamp);
CREATE INDEX idx_price_history_round ON price_history (auction_address, chain_id, round_id);
CREATE INDEX idx_price_history_chain ON price_history (chain_id);

-- Make price_history a hypertable for time-series optimization
SELECT create_hypertable('price_history', 'timestamp', if_not_exists => TRUE);

-- Insert some common tokens for reference across different chains
INSERT INTO tokens (address, symbol, name, decimals, chain_id) VALUES
-- Ethereum Mainnet (Chain ID 1)
('0x0000000000000000000000000000000000000000', 'ETH', 'Ethereum', 18, 1),
('0xA0b86a33E6441b8C87C83e4F8E3FBcE66A6F8cDf', 'USDC', 'USD Coin', 6, 1),
('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'WETH', 'Wrapped Ether', 18, 1),
('0xdAC17F958D2ee523a2206206994597C13D831ec7', 'USDT', 'Tether USD', 6, 1),
('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 'WBTC', 'Wrapped Bitcoin', 8, 1),
('0x6B175474E89094C44Da98b954EedeAC495271d0F', 'DAI', 'Dai Stablecoin', 18, 1),
-- Anvil testnet (Chain ID 31337)
('0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512', 'USDC', 'USD Coin', 6, 31337),
('0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0', 'USDT', 'Tether USD', 6, 31337),
('0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9', 'WETH', 'Wrapped Ether', 18, 31337),
('0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9', 'WBTC', 'Wrapped Bitcoin', 8, 31337),
('0x5FC8d32690cc91D4c39d9d3abcBD16989F875707', 'DAI', 'Dai Stablecoin', 18, 31337)
ON CONFLICT (address, chain_id) DO NOTHING;

-- ============================================================================
-- TRIGGERS AND FUNCTIONS
-- ============================================================================
-- Trigger to update auction_rounds statistics when sales happen
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the auction round statistics
    UPDATE auction_rounds 
    SET 
        total_sales = total_sales + 1,
        total_volume_sold = total_volume_sold + NEW.amount_taken,
        progress_percentage = LEAST(100.0, 
            ((total_volume_sold + NEW.amount_taken) * 100.0) / GREATEST(initial_available, 1)
        ),
        available_amount = GREATEST(0, initial_available - (total_volume_sold + NEW.amount_taken))
    WHERE 
        auction_address = NEW.auction_address 
        AND chain_id = NEW.chain_id 
        AND round_id = NEW.round_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update round statistics on new sales
CREATE TRIGGER trigger_update_round_statistics
    AFTER INSERT ON auction_sales
    FOR EACH ROW
    EXECUTE FUNCTION update_round_statistics();

-- Function to mark rounds as inactive when they expire
CREATE OR REPLACE FUNCTION check_round_expiry()
RETURNS void AS $$
BEGIN
    UPDATE auction_rounds ar
    SET is_active = FALSE,
        time_remaining = 0
    FROM auction_parameters ahp
    WHERE ar.auction_address = ahp.auction_address
        AND ar.chain_id = ahp.chain_id
        AND ar.is_active = TRUE
        AND ar.kicked_at + (ahp.auction_length || ' seconds')::INTERVAL < NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RINDEXER TABLE REFERENCES
-- ============================================================================
-- Note: The following tables will be created automatically by Rindexer:
-- 
-- - deployed_new_auction (from DeployedNewAuction event)
--   * auction (address)
--   * want_token (address) 
--   * deployer (address)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - auction_enabled (from AuctionEnabled event)
--   * from_token (address)
--   * auction (address)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - auction_round_kicked (from AuctionRoundKicked event)
--   * auction (address)
--   * from_token (address)
--   * round_id (uint256)
--   * available (uint256)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - auction_sale (from AuctionSale event)
--   * auction (address)
--   * round_id (uint256)
--   * sale_seq (uint256)
--   * taker (address)
--   * from_token (address)
--   * amount_taken (uint256)
--   * amount_paid (uint256)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - auction_disabled (from AuctionDisabled event)
--   * from_token (address)
--   * auction (address)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - updated_starting_price (from UpdatedStartingPrice event)
--   * auction (address)
--   * starting_price (uint256)
--   * block_number, transaction_hash, timestamp, chain_id, etc.
--
-- - updated_step_decay_rate (from UpdatedStepDecayRate event)
--   * auction (address)
--   * step_decay_rate (uint256) - indexed
--   * block_number, transaction_hash, timestamp, chain_id, etc.

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
-- Additional indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_auction_rounds_active_kicked_at 
    ON auction_rounds (kicked_at DESC) 
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_auction_sales_recent 
    ON auction_sales (timestamp DESC, auction_address, round_id, sale_seq);

-- Note: Cannot create time-based partial indexes with NOW() in schema
-- CREATE INDEX IF NOT EXISTS idx_price_history_recent 
--     ON price_history (timestamp DESC) 
--     WHERE timestamp > NOW() - INTERVAL '7 days';

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================
-- View for active auction rounds with all necessary data
CREATE OR REPLACE VIEW active_auction_rounds AS
SELECT 
    ar.*,
    ahp.want_token,
    ahp.decay_rate_percent,
    ahp.update_interval_minutes,
    ahp.auction_length,
    ahp.step_decay_rate,
    -- Calculate time remaining
    GREATEST(0, 
        ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
    )::INTEGER as calculated_time_remaining,
    -- Calculate seconds elapsed
    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
FROM auction_rounds ar
JOIN auction_parameters ahp 
    ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- View for recent sales with full context
CREATE OR REPLACE VIEW recent_auction_sales AS
SELECT 
    als.*,
    ar.kicked_at as round_kicked_at,
    ahp.want_token,
    t1.symbol as from_token_symbol,
    t1.name as from_token_name,
    t1.decimals as from_token_decimals,
    t2.symbol as to_token_symbol,
    t2.name as to_token_name,
    t2.decimals as to_token_decimals
FROM auction_sales als
JOIN auction_rounds ar 
    ON als.auction_address = ar.auction_address 
    AND als.chain_id = ar.chain_id 
    AND als.round_id = ar.round_id
JOIN auction_parameters ahp 
    ON als.auction_address = ahp.auction_address 
    AND als.chain_id = ahp.chain_id
LEFT JOIN tokens t1 
    ON als.from_token = t1.address 
    AND als.chain_id = t1.chain_id
LEFT JOIN tokens t2 
    ON als.to_token = t2.address 
    AND als.chain_id = t2.chain_id
ORDER BY als.timestamp DESC;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE tokens IS 'Token metadata cache for display purposes across multiple chains';
COMMENT ON TABLE auction_parameters IS 'Cache of Auction contract parameters (immutable values from deployment)';
COMMENT ON TABLE auction_rounds IS 'Tracks individual rounds within Auctions, created by kick events';
COMMENT ON TABLE auction_sales IS 'Tracks individual sales within rounds, created by take events';
COMMENT ON TABLE price_history IS 'Time-series price data for charting and analytics';
COMMENT ON VIEW active_auction_rounds IS 'Active rounds with calculated time remaining and elapsed time';
COMMENT ON VIEW recent_auction_sales IS 'Recent sales with full token and round context';

-- Note about Rindexer integration:
-- This schema works alongside Rindexer's automatic table generation.
-- Rindexer handles blockchain event storage, while this schema provides:
-- 1. Structured round and sale tracking with incrementing IDs
-- 2. Multi-chain support with chain_id fields
-- 3. Calculated fields for UI display (progress, time remaining)
-- 4. Time-series optimization with TimescaleDB hypertables
-- 5. Automatic statistics updates via triggers
-- 6. Performance-optimized views for common API queries