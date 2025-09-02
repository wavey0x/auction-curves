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
    address VARCHAR(100) UNIQUE NOT NULL,
    symbol VARCHAR(50),
    name VARCHAR(200),
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
-- AUCTIONS - MAIN AUCTION CONTRACTS TABLE
-- ============================================================================
-- Track individual auction contracts across chains
-- Each auction contract gets one entry with its metadata and configuration
CREATE TABLE auctions (
    auction_address VARCHAR(100) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    
    -- Auction parameters (renamed from ParameterizedAuction)
    price_update_interval INTEGER NOT NULL,
    step_decay DECIMAL(30,0) NOT NULL, -- RAY precision - DEPRECATED, use step_decay_rate
    step_decay_rate DECIMAL(30,0), -- New field: decay rate per 36-second step (e.g., 0.995 * 1e27)
    fixed_starting_price DECIMAL(30,0), -- NULL if dynamic
    auction_length INTEGER, -- seconds - now AUCTION_LENGTH constant
    starting_price DECIMAL(30,0), -- dynamic pricing value
    
    -- Token addresses
    want_token VARCHAR(100),
    
    -- Governance info
    deployer VARCHAR(100),
    receiver VARCHAR(100),
    governance VARCHAR(100),
    
    -- Discovery metadata
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    factory_address VARCHAR(100),
    auction_version VARCHAR(20) DEFAULT '0.1.0', -- Contract version: 0.0.1 (legacy) or 0.1.0 (new)
    
    -- Derived fields for UI
    decay_rate_percent DECIMAL(10,4), -- Calculated decay rate as percentage
    update_interval_minutes DECIMAL(10,2), -- Update interval in minutes
    
    PRIMARY KEY (auction_address, chain_id)
);

-- Create indexes for auctions table
CREATE INDEX idx_auctions_deployer ON auctions (deployer);
CREATE INDEX idx_auctions_factory ON auctions (factory_address);
CREATE INDEX idx_auctions_chain ON auctions (chain_id);

-- ============================================================================
-- ROUND TRACKING
-- ============================================================================
-- Track rounds within each Auction (supplements Rindexer kick events)
-- Each kick creates a new round with incremental round_id per Auction
CREATE TABLE rounds (
    auction_address VARCHAR(100) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    round_id INTEGER NOT NULL, -- Incremental per Auction: 1, 2, 3...
    from_token VARCHAR(100) NOT NULL,
    
    -- Round data
    kicked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_available NUMERIC(78,18) NOT NULL, -- Initial tokens for this round
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Current state (updated as round progresses)
    current_price DECIMAL(30,0), -- Current calculated price
    available_amount NUMERIC(78,18), -- Remaining tokens
    time_remaining INTEGER, -- Seconds until round ends
    seconds_elapsed INTEGER DEFAULT 0, -- Seconds since round started
    
    -- Round statistics
    total_takes INTEGER DEFAULT 0,
    total_volume_sold NUMERIC(78,18) DEFAULT 0,
    progress_percentage DECIMAL(5,2) DEFAULT 0, -- 0-100%
    
    -- Block data
    block_number BIGINT NOT NULL,
    transaction_hash VARCHAR(100) NOT NULL,
    
    PRIMARY KEY (auction_address, chain_id, round_id)
    -- FOREIGN KEY (auction_address, chain_id) REFERENCES auctions(auction_address, chain_id) -- Removed: not needed
);

-- Create indexes for rounds table
CREATE INDEX idx_rounds_active ON rounds (is_active);
CREATE INDEX idx_rounds_kicked_at ON rounds (kicked_at);
CREATE INDEX idx_rounds_chain ON rounds (chain_id);
CREATE INDEX idx_rounds_from_token ON rounds (from_token);

-- Note: rounds is NOT a hypertable (kept as regular table for better performance)

-- ============================================================================
-- TAKES TRACKING
-- ============================================================================
-- Track individual takes within rounds (supplements Rindexer take events)
-- Each take gets a sequence number within the round
CREATE TABLE takes (
    take_id VARCHAR(200), -- Format: {auction}-{roundId}-{takeSeq}
    auction_address VARCHAR(100) NOT NULL,
    chain_id INTEGER NOT NULL DEFAULT 1,
    round_id INTEGER NOT NULL,
    take_seq INTEGER NOT NULL, -- Sequence within round: 1, 2, 3...
    
    -- Sale data
    taker VARCHAR(100) NOT NULL,
    from_token VARCHAR(100) NOT NULL,
    to_token VARCHAR(100) NOT NULL, -- want_token
    amount_taken NUMERIC(78,18) NOT NULL, -- Amount of from_token purchased (human-readable)
    amount_paid NUMERIC(78,18) NOT NULL, -- Amount of to_token paid (human-readable)
    price NUMERIC(78,18) NOT NULL, -- want-per-from price (human-readable, 18 decimals)
    
    -- Timing
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    seconds_from_round_start INTEGER NOT NULL,
    
    -- Block data
    block_number BIGINT NOT NULL,
    transaction_hash VARCHAR(100) NOT NULL,
    log_index INTEGER NOT NULL,
    
    PRIMARY KEY (take_id, timestamp)
    -- FOREIGN KEY (auction_address, chain_id, round_id) REFERENCES auction_rounds(auction_address, chain_id, round_id) -- Removed: not needed
);

-- Create indexes for takes table
CREATE INDEX idx_takes_timestamp ON takes (timestamp);
CREATE INDEX idx_takes_chain ON takes (chain_id);
CREATE INDEX idx_takes_round ON takes (auction_address, chain_id, round_id);
CREATE INDEX idx_takes_taker ON takes (taker);
CREATE INDEX idx_takes_tx_hash ON takes (transaction_hash);

-- Make takes a hypertable for time-series optimization
SELECT create_hypertable('takes', 'timestamp', if_not_exists => TRUE);

-- ============================================================================
-- INDEXER STATE TRACKING
-- ============================================================================
-- Track indexer progress per blockchain network
CREATE TABLE indexer_state (
    chain_id INTEGER PRIMARY KEY,
    last_indexed_block INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for indexer_state table
CREATE INDEX idx_indexer_state_updated ON indexer_state (updated_at);


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
-- Trigger to update rounds statistics when takes happen
CREATE OR REPLACE FUNCTION update_round_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the round statistics
    UPDATE rounds 
    SET 
        total_takes = total_takes + 1,
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

-- Trigger to automatically update round statistics on new takes
CREATE TRIGGER trigger_update_round_statistics
    AFTER INSERT ON takes
    FOR EACH ROW
    EXECUTE FUNCTION update_round_statistics();

-- Function to mark rounds as inactive when they expire
CREATE OR REPLACE FUNCTION check_round_expiry()
RETURNS void AS $$
BEGIN
    UPDATE rounds ar
    SET is_active = FALSE,
        time_remaining = 0
    FROM auctions ahp
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
CREATE INDEX IF NOT EXISTS idx_rounds_active_kicked_at 
    ON rounds (kicked_at DESC) 
    WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_takes_recent 
    ON takes (timestamp DESC, auction_address, round_id, take_seq);

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
FROM rounds ar
JOIN auctions ahp 
    ON ar.auction_address = ahp.auction_address 
    AND ar.chain_id = ahp.chain_id
WHERE ar.is_active = TRUE
ORDER BY ar.kicked_at DESC;

-- View for recent takes with full context
CREATE OR REPLACE VIEW recent_takes AS
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
FROM takes als
JOIN rounds ar 
    ON als.auction_address = ar.auction_address 
    AND als.chain_id = ar.chain_id 
    AND als.round_id = ar.round_id
JOIN auctions ahp 
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
COMMENT ON TABLE auctions IS 'Main auction contracts table - one entry per deployed auction contract';
COMMENT ON TABLE rounds IS 'Tracks individual rounds within Auctions, created by kick events';
COMMENT ON TABLE takes IS 'Tracks individual takes within rounds, created by take events';
-- price_history removed (unused)
COMMENT ON VIEW active_auction_rounds IS 'Active rounds with calculated time remaining and elapsed time';
COMMENT ON VIEW recent_takes IS 'Recent takes with full token and round context';

-- Note about Rindexer integration:
-- This schema works alongside Rindexer's automatic table generation.
-- Rindexer handles blockchain event storage, while this schema provides:
-- 1. Structured round and sale tracking with incrementing IDs
-- 2. Multi-chain support with chain_id fields
-- 3. Calculated fields for UI display (progress, time remaining)
-- 4. Time-series optimization with TimescaleDB hypertables
-- 5. Automatic statistics updates via triggers
-- 6. Performance-optimized views for common API queries
