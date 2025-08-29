#!/usr/bin/env python3
"""
Database connection and session management for FastAPI.
"""

import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres@localhost:5432/auction"
)

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# SQLAlchemy base
Base = declarative_base()

async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def check_database_connection():
    """Check if database connection is working"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

async def get_rindexer_tables():
    """Get list of tables created by Rindexer"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (
                    table_name LIKE '%auction%' 
                    OR table_name LIKE '%auction_round%'
                    OR table_name LIKE '%auction_sale%'
                    OR table_name LIKE '%deployed%'
                )
                ORDER BY table_name
            """))
            return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get Rindexer tables: {e}")
        return []

class DatabaseQueries:
    """Centralized database query methods for Auction structure"""
    
    @staticmethod
    async def get_active_auctions(db: AsyncSession, chain_id: int = None):
        """Get all Auctions with active rounds"""
        chain_filter = "AND ar.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT 
                ar.auction_address,
                ar.chain_id,
                ar.round_id,
                ar.from_token,
                ar.kicked_at,
                ar.initial_available,
                ar.current_price,
                ar.available_amount,
                ar.time_remaining,
                ar.seconds_elapsed,
                ar.total_sales,
                ar.progress_percentage,
                ahp.want_token,
                ahp.decay_rate_percent,
                ahp.update_interval_minutes,
                ahp.auction_length,
                -- Calculate real-time values
                GREATEST(0, 
                    ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
                )::INTEGER as calculated_time_remaining,
                EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
            FROM auction_rounds ar
            JOIN auction_parameters ahp 
                ON ar.auction_address = ahp.auction_address 
                AND ar.chain_id = ahp.chain_id
            WHERE ar.is_active = TRUE
            {chain_filter}
            ORDER BY ar.kicked_at DESC
        """)
        
        params = {"chain_id": chain_id} if chain_id else {}
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_auction_details(db: AsyncSession, auction_address: str, chain_id: int = None):
        """Get detailed information about a specific Auction"""
        chain_filter = "AND ahp.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT 
                ahp.*,
                ar.kicked_at as last_kicked,
                ar.round_id as current_round_id,
                ar.available_amount as current_available,
                ar.current_price,
                ar.is_active as has_active_round,
                ar.total_sales as current_round_sales,
                ar.progress_percentage,
                -- Token info for want_token
                t2.symbol as want_token_symbol,
                t2.name as want_token_name,
                t2.decimals as want_token_decimals,
                -- Calculate time remaining for current round
                CASE WHEN ar.is_active THEN
                    GREATEST(0, 
                        ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
                    )::INTEGER
                ELSE 0 END as time_remaining
            FROM auction_parameters ahp
            LEFT JOIN auction_rounds ar 
                ON ahp.auction_address = ar.auction_address 
                AND ahp.chain_id = ar.chain_id
                AND ar.is_active = TRUE
            LEFT JOIN tokens t2 
                ON ahp.want_token = t2.address 
                AND ahp.chain_id = t2.chain_id
            WHERE ahp.auction_address = :auction_address
            {chain_filter}
            ORDER BY ar.kicked_at DESC NULLS LAST
            LIMIT 1
        """)
        
        params = {"auction_address": auction_address}
        if chain_id:
            params["chain_id"] = chain_id
            
        result = await db.execute(query, params)
        return result.fetchone()
    
    @staticmethod
    async def get_auction_rounds(db: AsyncSession, auction_address: str, from_token: str = None, chain_id: int = None, limit: int = 50):
        """Get round history for an Auction"""
        chain_filter = "AND ar.chain_id = :chain_id" if chain_id else ""
        token_filter = "AND ar.from_token = :from_token" if from_token else ""
        
        query = text(f"""
            SELECT 
                ar.*,
                ahp.want_token,
                ahp.auction_length,
                -- Calculate time remaining for active rounds
                CASE WHEN ar.is_active THEN
                    GREATEST(0, 
                        ahp.auction_length - EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))
                    )::INTEGER
                ELSE 0 END as calculated_time_remaining,
                EXTRACT(EPOCH FROM (NOW() - ar.kicked_at))::INTEGER as calculated_seconds_elapsed
            FROM auction_rounds ar
            JOIN auction_parameters ahp 
                ON ar.auction_address = ahp.auction_address 
                AND ar.chain_id = ahp.chain_id
            WHERE ar.auction_address = :auction_address
            {chain_filter}
            {token_filter}
            ORDER BY ar.round_id DESC
            LIMIT :limit
        """)
        
        params = {
            "auction_address": auction_address,
            "limit": limit
        }
        if chain_id:
            params["chain_id"] = chain_id
        if from_token:
            params["from_token"] = from_token
            
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_auction_sales(db: AsyncSession, auction_address: str, round_id: int = None, chain_id: int = None, limit: int = 50):
        """Get sales history for an Auction"""
        chain_filter = "AND als.chain_id = :chain_id" if chain_id else ""
        round_filter = "AND als.round_id = :round_id" if round_id else ""
        
        query = text(f"""
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
            WHERE als.auction_address = :auction_address
            {chain_filter}
            {round_filter}
            ORDER BY als.timestamp DESC
            LIMIT :limit
        """)
        
        params = {
            "auction_address": auction_address,
            "limit": limit
        }
        if chain_id:
            params["chain_id"] = chain_id
        if round_id:
            params["round_id"] = round_id
            
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_price_history(db: AsyncSession, auction_address: str, round_id: int = None, chain_id: int = None, hours: int = 24):
        """Get price history for an Auction round"""
        chain_filter = "AND ph.chain_id = :chain_id" if chain_id else ""
        round_filter = "AND ph.round_id = :round_id" if round_id else ""
        
        query = text(f"""
            SELECT 
                ph.timestamp,
                ph.price,
                ph.available_amount,
                ph.seconds_from_round_start,
                ph.round_id,
                ph.from_token
            FROM price_history ph
            WHERE ph.auction_address = :auction_address
            AND ph.timestamp >= NOW() - INTERVAL '{hours} hours'
            {chain_filter}
            {round_filter}
            ORDER BY ph.timestamp ASC
        """)
        
        params = {
            "auction_address": auction_address
        }
        if chain_id:
            params["chain_id"] = chain_id
        if round_id:
            params["round_id"] = round_id
            
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_all_tokens(db: AsyncSession, chain_id: int = None):
        """Get all token information"""
        chain_filter = "WHERE chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT address, symbol, name, decimals, chain_id
            FROM tokens
            {chain_filter}
            ORDER BY chain_id, symbol
        """)
        
        params = {"chain_id": chain_id} if chain_id else {}
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_system_stats(db: AsyncSession, chain_id: int = None):
        """Get overall system statistics"""
        chain_filter = "WHERE ahp.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT 
                COUNT(DISTINCT ahp.auction_address) as total_auctions,
                COUNT(DISTINCT CASE WHEN ar.is_active THEN ar.auction_address END) as active_auctions,
                COUNT(DISTINCT t.address) as unique_tokens,
                COUNT(DISTINCT ar.round_id) as total_rounds,
                COUNT(als.sale_id) as total_sales,
                COUNT(DISTINCT als.taker) as total_participants
            FROM auction_parameters ahp
            LEFT JOIN auction_rounds ar 
                ON ahp.auction_address = ar.auction_address
                AND ahp.chain_id = ar.chain_id
            LEFT JOIN auction_sales als
                ON ar.auction_address = als.auction_address
                AND ar.chain_id = als.chain_id
            LEFT JOIN tokens t 
                ON ahp.chain_id = t.chain_id
            {chain_filter}
        """)
        
        params = {"chain_id": chain_id} if chain_id else {}
        result = await db.execute(query, params)
        return result.fetchone()
    
    @staticmethod
    async def get_recent_sales_activity(db: AsyncSession, limit: int = 25, chain_id: int = None):
        """Get recent sales activity across all Auctions"""
        chain_filter = "WHERE als.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT 
                als.sale_id as id,
                'take' as event_type,
                als.auction_address,
                als.chain_id,
                als.from_token,
                als.to_token,
                als.amount_taken as amount,
                als.price,
                als.taker as participant,
                EXTRACT(EPOCH FROM als.timestamp)::INTEGER as timestamp,
                als.transaction_hash as tx_hash,
                als.block_number,
                als.round_id,
                als.sale_seq
            FROM auction_sales als
            {chain_filter}
            ORDER BY als.timestamp DESC
            LIMIT :limit
        """)
        
        params = {"limit": limit}
        if chain_id:
            params["chain_id"] = chain_id
            
        result = await db.execute(query, params)
        return result.fetchall()

# Initialize database connection check
async def init_database():
    """Initialize database connection and verify setup"""
    logger.info("Checking database connection...")
    
    if await check_database_connection():
        logger.info("✅ Database connection successful")
        
        # Check for Rindexer tables
        tables = await get_rindexer_tables()
        logger.info(f"📊 Found {len(tables)} auction-related tables: {', '.join(tables)}")
        
        return True
    else:
        logger.error("❌ Database connection failed")
        return False

if __name__ == "__main__":
    # Test database connection
    async def test_connection():
        success = await init_database()
        if success:
            async with AsyncSessionLocal() as session:
                stats = await DatabaseQueries.get_system_stats(session)
                logger.info(f"System stats: {dict(stats) if stats else 'No data yet'}")
                
                # Test the new query methods
                active_auctions = await DatabaseQueries.get_active_auctions(session)
                logger.info(f"Active auctions: {len(active_auctions)}")
                
                tokens = await DatabaseQueries.get_all_tokens(session)
                logger.info(f"Total tokens: {len(tokens)}")
                
                recent_sales = await DatabaseQueries.get_recent_sales_activity(session, limit=5)
                logger.info(f"Recent sales: {len(recent_sales)}")

    asyncio.run(test_connection())