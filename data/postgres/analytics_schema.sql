-- Auction House Analytics Schema
-- This schema adds analytics and calculated fields ON TOP of Rindexer's automatically generated tables
-- Rindexer will create the base event tables automatically

-- Enable TimescaleDB extension for time-series data
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- PRICE HISTORY (Calculated price points over time)
-- ============================================================================
CREATE TABLE price_history (
    auction_address VARCHAR(42) NOT NULL,
    from_token VARCHAR(42) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    block_number BIGINT NOT NULL,
    price DECIMAL(30,0) NOT NULL,
    available_amount DECIMAL(30,0) NOT NULL,
    seconds_from_kick INTEGER NOT NULL,
    price_change_pct DECIMAL(10, 4), -- vs previous data point
    
    PRIMARY KEY (auction_address, from_token, timestamp),
    INDEX idx_price_auction (auction_address),
    INDEX idx_price_token (from_token),
    INDEX idx_price_time (timestamp),
    INDEX idx_price_block (block_number)
);

-- Convert to hypertable for time-series performance
SELECT create_hypertable('price_history', 'timestamp');

-- ============================================================================
-- AUCTION ROUND ANALYTICS (Aggregated data per auction round)
-- ============================================================================
CREATE TABLE auction_round_analytics (
    id SERIAL PRIMARY KEY,
    auction_address VARCHAR(42) NOT NULL,
    from_token VARCHAR(42) NOT NULL,
    kicked_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Calculated metrics
    initial_available DECIMAL(30,0),
    total_taken DECIMAL(30,0) DEFAULT 0,
    total_revenue DECIMAL(30,0) DEFAULT 0,
    participant_count INTEGER DEFAULT 0,
    final_price DECIMAL(30,0),
    
    -- Performance metrics
    avg_price DECIMAL(30,0),
    min_price DECIMAL(30,0),
    max_price DECIMAL(30,0),
    duration_seconds INTEGER,
    completion_percentage DECIMAL(5,2), -- what % of tokens were sold
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, completed, expired
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_round_analytics_auction (auction_address),
    INDEX idx_round_analytics_token (from_token),
    INDEX idx_round_analytics_kicked (kicked_at),
    INDEX idx_round_analytics_status (status)
);

-- ============================================================================
-- PARTICIPANT ANALYTICS (Aggregated participant behavior)
-- ============================================================================
CREATE TABLE participant_analytics (
    participant VARCHAR(42) PRIMARY KEY,
    
    -- Activity metrics
    total_participations INTEGER DEFAULT 0,
    unique_auctions INTEGER DEFAULT 0,
    total_spent DECIMAL(30,0) DEFAULT 0,
    total_tokens_acquired DECIMAL(30,0) DEFAULT 0,
    
    -- Behavior metrics
    avg_price_paid DECIMAL(30,0),
    avg_time_to_participate INTEGER, -- seconds after kick
    preferred_auction_stage VARCHAR(20), -- early, middle, late
    
    -- Timestamps
    first_participation TIMESTAMP WITH TIME ZONE,
    last_participation TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_participant_participations (total_participations),
    INDEX idx_participant_spent (total_spent)
);

-- ============================================================================
-- VIEWS THAT READ FROM RINDEXER TABLES
-- ============================================================================
-- Note: These views reference tables that Rindexer will create automatically
-- Table names are inferred based on event names: deployed_new_auction, auction_kicked, etc.

-- Active auctions (assumes Rindexer creates 'auction_kicked' table)
CREATE VIEW active_auctions AS
SELECT 
    ak.auction as auction_address,
    ak.from_token,
    ak.available as initial_available,
    ak.timestamp as kicked_at,
    EXTRACT(EPOCH FROM (NOW() - ak.timestamp)) as seconds_elapsed
FROM auction_kicked ak
-- Add logic to filter only currently active auctions
WHERE ak.timestamp + INTERVAL '24 hours' > NOW(); -- Assume 24h default, will need to be adjusted

-- Auction performance metrics
CREATE VIEW auction_metrics AS
SELECT 
    ara.auction_address,
    COUNT(*) as total_rounds,
    AVG(ara.participant_count) as avg_participants,
    SUM(ara.total_taken) as total_volume,
    SUM(ara.total_revenue) as total_revenue,
    AVG(ara.final_price) as avg_final_price,
    AVG(ara.completion_percentage) as avg_completion_rate,
    MIN(ara.kicked_at) as first_auction,
    MAX(ara.kicked_at) as last_auction
FROM auction_round_analytics ara
GROUP BY ara.auction_address;

-- Top participants
CREATE VIEW top_participants AS
SELECT 
    participant,
    total_participations,
    unique_auctions,
    total_spent,
    total_tokens_acquired,
    avg_price_paid,
    first_participation,
    last_participation
FROM participant_analytics
ORDER BY total_participations DESC;

-- ============================================================================
-- FUNCTIONS FOR PRICE CALCULATIONS
-- ============================================================================
CREATE OR REPLACE FUNCTION calculate_auction_price(
    p_price_update_interval INTEGER,
    p_step_decay DECIMAL,
    p_fixed_starting_price DECIMAL,
    p_starting_price DECIMAL,
    p_initial_available DECIMAL,
    p_kicked_at TIMESTAMP WITH TIME ZONE,
    p_auction_length INTEGER,
    p_timestamp TIMESTAMP WITH TIME ZONE
) RETURNS DECIMAL AS $$
DECLARE
    seconds_elapsed INTEGER;
    steps_elapsed INTEGER;
    decay_factor DECIMAL;
    initial_price DECIMAL;
    current_price DECIMAL;
BEGIN
    -- Calculate seconds elapsed since kick
    seconds_elapsed := EXTRACT(EPOCH FROM (p_timestamp - p_kicked_at));
    
    -- If auction hasn't started or has ended, return 0
    IF seconds_elapsed < 0 OR seconds_elapsed > p_auction_length THEN
        RETURN 0;
    END IF;
    
    -- Calculate steps elapsed (floor division)
    steps_elapsed := seconds_elapsed / p_price_update_interval;
    
    -- Calculate decay factor: stepDecay^stepsElapsed
    decay_factor := POWER(p_step_decay / 1e27, steps_elapsed);
    
    -- Determine starting price
    IF p_fixed_starting_price IS NOT NULL AND p_fixed_starting_price > 0 THEN
        initial_price := p_fixed_starting_price;
    ELSE
        initial_price := p_starting_price;
    END IF;
    
    -- Calculate current price
    current_price := (initial_price * decay_factor * 1e27) / p_initial_available / 1e27;
    
    RETURN current_price;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS FOR UPDATING ANALYTICS
-- ============================================================================
-- These will be created once we know the exact table names that Rindexer generates

-- Example trigger function (will need adjustment based on actual Rindexer table names)
CREATE OR REPLACE FUNCTION update_round_analytics()
RETURNS TRIGGER AS $$
BEGIN
    -- This will be implemented once we see Rindexer's actual table structure
    -- It will update auction_round_analytics when new takes happen
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP POLICIES
-- ============================================================================
-- Retention policies for time-series data
SELECT add_retention_policy('price_history', INTERVAL '3 years');

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE price_history IS 'Calculated price points over time for charting (supplements Rindexer event data)';
COMMENT ON TABLE auction_round_analytics IS 'Aggregated analytics per auction round (built from Rindexer events)';
COMMENT ON TABLE participant_analytics IS 'Participant behavior metrics (built from Rindexer events)';

COMMENT ON VIEW active_auctions IS 'Currently active auctions (reads from Rindexer auction_kicked table)';
COMMENT ON VIEW auction_metrics IS 'Performance metrics per auction contract';
COMMENT ON VIEW top_participants IS 'Participant leaderboard';

COMMENT ON FUNCTION calculate_auction_price IS 'Calculate auction price at any timestamp using parameterized formula';