#!/usr/bin/env python3
"""
Database connection and session management for FastAPI.
"""

import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

# Load environment variables from .env file
load_dotenv("../../.env")

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres@localhost:5432/auction"  # Fixed default to use correct user
)

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,  # Enable SQL logging for debugging
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


class DatabaseQueries:
    """Centralized database query methods for Auction structure"""
    
    
    @staticmethod
    async def get_auctions(db: AsyncSession, active_only: bool = False, chain_id: int = None):
        """Get auctions with optional active filter"""
        chain_filter = "AND ahp.chain_id = :chain_id" if chain_id else ""
        
        if active_only:
            # For active-only, only return auctions with active rounds
            query = text(f"""
                SELECT DISTINCT
                    ahp.auction_address,
                    ahp.chain_id,
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
                    ahp.decay_rate,
                    ahp.update_interval,
                    ahp.auction_length,
                    TRUE as is_active
                FROM auctions ahp
                INNER JOIN rounds ar 
                    ON ahp.auction_address = ar.auction_address 
                    AND ahp.chain_id = ar.chain_id
                    AND ar.is_active = TRUE
                WHERE 1=1
                {chain_filter}
                ORDER BY ar.kicked_at DESC
            """)
        else:
            # For all auctions, get each auction once with their most recent active round (if any)
            query = text(f"""
                SELECT DISTINCT ON (ahp.auction_address, ahp.chain_id)
                    ahp.auction_address,
                    ahp.chain_id,
                    COALESCE(ar.round_id, 0) as round_id,
                    COALESCE(ar.from_token, '') as from_token,
                    COALESCE(ar.kicked_at, 0) as kicked_at,
                    COALESCE(ar.initial_available, 0) as initial_available,
                    COALESCE(ar.current_price, 0) as current_price,
                    COALESCE(ar.available_amount, 0) as available_amount,
                    COALESCE(ar.time_remaining, 0) as time_remaining,
                    COALESCE(ar.seconds_elapsed, 0) as seconds_elapsed,
                    COALESCE(ar.total_sales, 0) as total_sales,
                    COALESCE(ar.progress_percentage, 0) as progress_percentage,
                    ahp.want_token,
                    ahp.decay_rate,
                    ahp.update_interval,
                    ahp.auction_length,
                    COALESCE(ar.is_active, FALSE) as is_active,
                    -- Want token info
                    wt.symbol as want_token_symbol,
                    wt.name as want_token_name,
                    wt.decimals as want_token_decimals,
                    -- From token info (from current round if any)
                    ft.symbol as from_token_symbol,
                    ft.name as from_token_name,
                    ft.decimals as from_token_decimals,
                    -- Get enabled tokens as JSON array
                    (
                        SELECT COALESCE(
                            json_agg(
                                json_build_object(
                                    'address', et.token_address,
                                    'symbol', COALESCE(et_tokens.symbol, 'Unknown'),
                                    'name', COALESCE(et_tokens.name, 'Unknown'),
                                    'decimals', COALESCE(et_tokens.decimals, 18),
                                    'chain_id', et.chain_id
                                ) ORDER BY et.enabled_at ASC
                            ), '[]'::json
                        )
                        FROM enabled_tokens et
                        LEFT JOIN tokens et_tokens ON LOWER(et.token_address) = LOWER(et_tokens.address) AND et.chain_id = et_tokens.chain_id
                        WHERE et.auction_address = ahp.auction_address AND et.chain_id = ahp.chain_id
                    ) as from_tokens_json
                FROM auctions ahp
                LEFT JOIN rounds ar 
                    ON ahp.auction_address = ar.auction_address 
                    AND ahp.chain_id = ar.chain_id
                LEFT JOIN tokens wt
                    ON LOWER(ahp.want_token) = LOWER(wt.address)
                    AND ahp.chain_id = wt.chain_id
                LEFT JOIN tokens ft
                    ON LOWER(ar.from_token) = LOWER(ft.address)
                    AND ar.chain_id = ft.chain_id
                WHERE 1=1
                {chain_filter}
                ORDER BY ahp.auction_address, ahp.chain_id, ar.is_active DESC NULLS LAST, ar.kicked_at DESC NULLS LAST
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
                        ahp.auction_length - (EXTRACT(EPOCH FROM NOW()) - ar.kicked_at)
                    )::INTEGER
                ELSE 0 END as time_remaining
            FROM auctions ahp
            LEFT JOIN rounds ar 
                ON ahp.auction_address = ar.auction_address 
                AND ahp.chain_id = ar.chain_id
                AND ar.is_active = TRUE
            LEFT JOIN tokens t2 
                ON ahp.want_token = t2.address 
                AND ahp.chain_id = t2.chain_id
            WHERE LOWER(ahp.auction_address) = LOWER(:auction_address)
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
    async def get_enabled_tokens(db: AsyncSession, auction_address: str, chain_id: int):
        """Get enabled tokens for a specific auction with token metadata"""
        query = text("""
            SELECT 
                et.token_address,
                COALESCE(t.symbol, 'Unknown') as token_symbol,
                COALESCE(t.name, 'Unknown') as token_name,
                COALESCE(t.decimals, 18) as token_decimals,
                et.chain_id
            FROM enabled_tokens et
            LEFT JOIN tokens t 
                ON LOWER(et.token_address) = LOWER(t.address) 
                AND et.chain_id = t.chain_id
            WHERE LOWER(et.auction_address) = LOWER(:auction_address)
            AND et.chain_id = :chain_id
            ORDER BY et.enabled_at ASC
        """)
        
        params = {"auction_address": auction_address, "chain_id": chain_id}
        result = await db.execute(query, params)
        return result.fetchall()
    
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
                        ahp.auction_length - (EXTRACT(EPOCH FROM NOW()) - ar.kicked_at)
                    )::INTEGER
                ELSE 0 END as calculated_time_remaining,
                (EXTRACT(EPOCH FROM NOW()) - ar.kicked_at)::INTEGER as calculated_seconds_elapsed
            FROM rounds ar
            JOIN auctions ahp 
                ON LOWER(ar.auction_address) = LOWER(ahp.auction_address) 
                AND ar.chain_id = ahp.chain_id
            WHERE LOWER(ar.auction_address) = LOWER(:auction_address)
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
            WHERE LOWER(als.auction_address) = LOWER(:auction_address)
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
            WHERE LOWER(ph.auction_address) = LOWER(:auction_address)
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
            FROM auctions ahp
            LEFT JOIN rounds ar 
                ON ahp.auction_address = ar.auction_address
                AND ahp.chain_id = ar.chain_id
            LEFT JOIN takes als
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
            FROM takes als
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
        
        logger.info("📊 Database connection verified")
        
        return True
    else:
        logger.error("❌ Database connection failed")
        return False

# ========================================
# Data Provider Interfaces (consolidated from data_service.py)
# ========================================

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

# Import models - we'll need these for the consolidated version
try:
    from models.auction import (
        AuctionListItem,
        AuctionResponse,
        Take,
        AuctionRoundInfo,
        TokenInfo,
        SystemStats,
        AuctionParameters,
        AuctionActivity
    )
    from config import get_settings, is_mock_mode, is_development_mode
except ImportError:
    # Handle imports for when running standalone
    pass


class DataProvider(ABC):
    """Abstract base class for data providers"""
    
    @abstractmethod
    async def get_auctions(
        self, 
        status: str = "all", 
        page: int = 1, 
        limit: int = 20,
        chain_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get paginated list of auctions"""
        pass
    
    @abstractmethod
    async def get_auction_details(self, auction_address: str, chain_id: int) -> 'AuctionResponse':
        """Get detailed auction information"""
        pass
    
    @abstractmethod
    async def get_auction_takes(
        self, 
        auction_address: str, 
        round_id: Optional[int] = None, 
        limit: int = 50,
        chain_id: int = None
    ) -> List['Take']:
        """Get takes for an auction"""
        pass
    
    @abstractmethod
    async def get_auction_rounds(
        self, 
        auction_address: str, 
        from_token: str, 
        limit: int = 50,
        chain_id: int = None
    ) -> Dict[str, Any]:
        """Get round history for an auction"""
        pass
    
    @abstractmethod
    async def get_tokens(self) -> Dict[str, Any]:
        """Get all tokens"""
        pass
    
    @abstractmethod
    async def get_system_stats(self, chain_id: Optional[int] = None) -> 'SystemStats':
        """Get system statistics"""
        pass


class MockDataProvider(DataProvider):
    """Mock data provider for testing and development"""
    
    def __init__(self):
        self.mock_tokens = [
            TokenInfo(
                address="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", 
                symbol="USDC", 
                name="USD Coin", 
                decimals=6, 
                chain_id=31337
            ),
            TokenInfo(
                address="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", 
                symbol="USDT", 
                name="Tether USD", 
                decimals=6, 
                chain_id=31337
            ),
            TokenInfo(
                address="0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", 
                symbol="WETH", 
                name="Wrapped Ether", 
                decimals=18, 
                chain_id=31337
            )
        ]
    
    async def get_auctions(self, status="all", page=1, limit=20, chain_id=None):
        # Simple mock response
        return {
            "auctions": [],
            "total": 0,
            "page": page,
            "per_page": limit,
            "has_next": False
        }

    async def get_auction_details(self, auction_address: str, chain_id: int) -> AuctionResponse:
        """Get mock auction details"""
        # Return simplified mock data
        current_round = AuctionRoundInfo(
            round_id=1,
            kicked_at=datetime.now() - timedelta(minutes=30),
            initial_available="1000000000000000000000",
            is_active=True,
            current_price="950000",
            available_amount="800000000000000000000",
            time_remaining=1800,
            seconds_elapsed=1800,
            total_sales=5,
            progress_percentage=20.0
        )
        
        return AuctionResponse(
            address=auction_address,
            chain_id=chain_id,
            deployer="0x1234567890123456789012345678901234567890",
            from_tokens=self.mock_tokens[:2],
            want_token=self.mock_tokens[2],
            parameters=AuctionParameters(
                price_update_interval=60,
                step_decay="995000000000000000000000000",
                auction_length=3600,
                starting_price="1000000"
            ),
            current_round=current_round,
            activity=AuctionActivity(
                total_participants=10,
                total_volume="500000000",
                total_rounds=1,
                total_sales=5,
                recent_sales=[]
            ),
            deployed_at=datetime.now() - timedelta(days=30),
            last_kicked=datetime.now() - timedelta(minutes=30)
        )

    async def get_auction_takes(self, auction_address: str, round_id: Optional[int] = None, limit: int = 50, chain_id: int = None) -> List[Take]:
        """Generate mock takes data"""
        return []

    async def get_auction_rounds(self, auction_address: str, from_token: str, limit: int = 50, chain_id: int = None) -> Dict[str, Any]:
        """Generate mock rounds data"""
        return {
            "auction": auction_address,
            "from_token": from_token,
            "rounds": [],
            "total": 0
        }

    async def get_tokens(self) -> Dict[str, Any]:
        """Return mock tokens"""
        return {
            "tokens": self.mock_tokens,
            "count": len(self.mock_tokens)
        }
    
    async def get_system_stats(self, chain_id: Optional[int] = None) -> SystemStats:
        """Return mock system stats"""
        return SystemStats(
            total_auctions=5,
            active_auctions=2,
            total_participants=50,
            total_volume="1000000000",
            total_sales=100
        )


class DatabaseDataProvider(DataProvider):
    """Database data provider using direct SQL queries"""
    
    def __init__(self):
        pass

    async def get_auctions(self, status="all", page=1, limit=20, chain_id=None):
        """Get auctions from database using async queries"""
        try:
            async with AsyncSessionLocal() as session:
                # Get auctions from database (all or active based on status filter)
                active_only = status == "active"
                auctions_data = await DatabaseQueries.get_auctions(session, active_only, chain_id)
                auctions = []
                
                # Process auctions data
                for auction_row in auctions_data:
                    auction = {
                        "address": auction_row.auction_address,
                        "chain_id": auction_row.chain_id,
                        "from_tokens": auction_row.from_tokens_json if hasattr(auction_row, 'from_tokens_json') and auction_row.from_tokens_json else [],
                        "want_token": {"address": auction_row.want_token, "symbol": auction_row.want_token_symbol or "Unknown", "name": auction_row.want_token_name or "Unknown", "decimals": auction_row.want_token_decimals or 18, "chain_id": auction_row.chain_id},
                        "current_round": {
                            "round_id": auction_row.round_id,
                            "is_active": True,
                            "total_sales": auction_row.total_sales
                        } if auction_row.round_id else None,
                        "last_kicked": auction_row.kicked_at,
                        "decay_rate": 0.005,
                        "update_interval": 60
                    }
                    auctions.append(auction)

                logger.info(f"Loaded {len(auctions)} auctions from database")
                
                # Pagination
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                paginated_auctions = auctions[start_idx:end_idx]
                
                return {
                    "auctions": paginated_auctions,
                    "total": len(auctions),
                    "page": page,
                    "per_page": limit,
                    "has_next": end_idx < len(auctions)
                }
        except Exception as e:
            logger.error(f"Database error in get_auctions: {e}")
            raise Exception(f"Failed to fetch auctions from database: {e}")

    async def get_tokens(self) -> Dict[str, Any]:
        """Get tokens from database"""
        try:
            async with AsyncSessionLocal() as session:
                tokens_data = await DatabaseQueries.get_all_tokens(session)
                tokens = []
                for token_row in tokens_data:
                    token = TokenInfo(
                        address=token_row.address,
                        symbol=token_row.symbol,
                        name=token_row.name,
                        decimals=token_row.decimals,
                        chain_id=token_row.chain_id
                    )
                    tokens.append(token)
                
                return {
                    "tokens": tokens,
                    "count": len(tokens)
                }
        except Exception as e:
            logger.error(f"Database error in get_tokens: {e}")
            raise Exception(f"Failed to fetch tokens from database: {e}")

    async def get_auction_details(self, auction_address: str, chain_id: int) -> AuctionResponse:
        """Get auction details from database"""
        try:
            async with AsyncSessionLocal() as session:
                logger.info(f"Querying auction details for {auction_address} on chain {chain_id}")
                
                # Get auction details from database
                auction_data = await DatabaseQueries.get_auction_details(session, auction_address, chain_id)
                
                if not auction_data:
                    raise Exception(f"Auction {auction_address} not found in database")

                # Use actual database data
                want_token = TokenInfo(
                    address=auction_data.want_token,
                    symbol=auction_data.want_token_symbol or "Unknown",
                    name=auction_data.want_token_name or "Unknown", 
                    decimals=auction_data.want_token_decimals or 18,
                    chain_id=chain_id
                )
                
                parameters = AuctionParameters(
                    price_update_interval=auction_data.update_interval or 60,
                    step_decay=str(auction_data.step_decay) if auction_data.step_decay else "995000000000000000000000000",
                    auction_length=auction_data.auction_length or 3600,
                    starting_price=str(auction_data.starting_price) if auction_data.starting_price else "0"
                )
                
                current_round = None
                if auction_data.has_active_round and auction_data.current_round_id:
                    current_round = AuctionRoundInfo(
                        round_id=auction_data.current_round_id,
                        kicked_at=datetime.fromtimestamp(auction_data.last_kicked) if auction_data.last_kicked else datetime.now(),
                        initial_available=str(auction_data.current_available or 0),
                        is_active=auction_data.has_active_round,
                        current_price=str(auction_data.current_price or 0),
                        available_amount=str(auction_data.current_available or 0),
                        time_remaining=auction_data.time_remaining or 0,
                        seconds_elapsed=0,
                        total_sales=auction_data.current_round_sales or 0,
                        progress_percentage=auction_data.progress_percentage or 0.0
                    )
                
                # Get enabled tokens for this auction
                enabled_tokens_data = await DatabaseQueries.get_enabled_tokens(session, auction_address, chain_id)
                from_tokens = [
                    TokenInfo(
                        address=token.token_address,
                        symbol=token.token_symbol or "Unknown",
                        name=token.token_name or "Unknown",
                        decimals=token.token_decimals or 18,
                        chain_id=token.chain_id
                    )
                    for token in enabled_tokens_data
                ]
                
                return AuctionResponse(
                    address=auction_address,
                    chain_id=chain_id,
                    deployer=auction_data.deployer or "0x0000000000000000000000000000000000000000",
                    from_tokens=from_tokens,
                    want_token=want_token,
                    parameters=parameters,
                    current_round=current_round,
                    activity=AuctionActivity(
                        total_participants=0,  # TODO: Calculate from takes table
                        total_volume="0",      # TODO: Calculate from takes table
                        total_rounds=0,        # TODO: Calculate from rounds table
                        total_takes=0,         # TODO: Calculate from takes table
                        recent_takes=[]        # TODO: Get from takes table
                    ),
                    deployed_at=datetime.fromtimestamp(auction_data.timestamp) if auction_data.timestamp else datetime.now(),
                    last_kicked=datetime.fromtimestamp(auction_data.last_kicked) if auction_data.last_kicked else None
                )
        except Exception as e:
            logger.error(f"Database error in get_auction_details: {e}")
            raise Exception(f"Failed to fetch auction details from database: {e}")

    async def get_auction_takes(self, auction_address: str, round_id: Optional[int] = None, limit: int = 50, chain_id: int = None) -> List[Take]:
        """Get takes from database"""
        try:
            async with AsyncSessionLocal() as session:
                # Use the proper method name for sales/takes
                takes_data = await DatabaseQueries.get_auction_sales(
                    session, auction_address, round_id, chain_id, limit
                )
                
                takes = []
                for take_row in takes_data:
                    take = Take(
                        sale_id=str(take_row.sale_id) if take_row.sale_id else f"sale_{take_row.sale_seq}",
                        auction=take_row.auction_address,
                        chain_id=take_row.chain_id,
                        round_id=take_row.round_id,
                        sale_seq=take_row.sale_seq,
                        taker=take_row.taker,
                        amount_taken=str(take_row.amount_taken),
                        amount_paid=str(take_row.amount_paid),
                        price=str(take_row.price),
                        timestamp=take_row.timestamp.isoformat() if hasattr(take_row.timestamp, 'isoformat') else str(take_row.timestamp),
                        tx_hash=take_row.transaction_hash,
                        block_number=take_row.block_number
                    )
                    takes.append(take)
                
                logger.info(f"Loaded {len(takes)} takes from database for {auction_address}")
                return takes
        except Exception as e:
            logger.error(f"Database error in get_auction_takes: {e}")
            raise Exception(f"Failed to fetch auction takes from database: {e}")

    async def get_auction_rounds(self, auction_address: str, from_token: str, limit: int = 50, chain_id: int = None) -> Dict[str, Any]:
        """Get auction rounds from database using direct SQL query"""
        try:
            async with AsyncSessionLocal() as session:
                logger.info(f"Querying rounds for auction {auction_address}, from_token {from_token}, chain_id {chain_id}")
                
                # Use a direct SQL query to get the data
                # Add chain_id filter if provided
                chain_filter = "AND ar.chain_id = :chain_id" if chain_id else ""
                
                query = text(f"""
                    SELECT 
                        ar.round_id,
                        ar.kicked_at,
                        ar.initial_available,
                        ar.is_active,
                        ar.total_sales
                    FROM rounds ar
                    JOIN auctions ahp 
                        ON LOWER(ar.auction_address) = LOWER(ahp.auction_address) 
                        AND ar.chain_id = ahp.chain_id
                    WHERE LOWER(ar.auction_address) = LOWER(:auction_address)
                        AND ar.from_token = :from_token
                        {chain_filter}
                    ORDER BY ar.round_id DESC
                    LIMIT :limit
                """)
                
                params = {
                    "auction_address": auction_address,
                    "from_token": from_token,
                    "limit": limit
                }
                if chain_id:
                    params["chain_id"] = chain_id
                
                result = await session.execute(query, params)
                rounds_data = result.fetchall()
                
                logger.info(f"Database returned {len(rounds_data)} rounds")
                
                rounds = []
                for round_row in rounds_data:
                    # kicked_at is now a Unix timestamp (bigint) after migration
                    kicked_at_iso = datetime.fromtimestamp(round_row.kicked_at).isoformat()
                    
                    round_info = {
                        "round_id": round_row.round_id,
                        "kicked_at": kicked_at_iso,
                        "initial_available": str(round_row.initial_available) if round_row.initial_available else "0",
                        "is_active": round_row.is_active or False,
                        "total_sales": round_row.total_sales or 0
                    }
                    rounds.append(round_info)
                
                logger.info(f"Successfully loaded {len(rounds)} rounds from database for {auction_address}")
                return {
                    "auction": auction_address,
                    "from_token": from_token,
                    "rounds": rounds,
                    "total": len(rounds)
                }
        except Exception as e:
            logger.error(f"Database error in get_auction_rounds: {e}")
            raise Exception(f"Failed to fetch auction rounds from database: {e}")

    async def get_system_stats(self, chain_id: Optional[int] = None) -> SystemStats:
        """Get system stats from database"""
        try:
            async with AsyncSessionLocal() as session:
                stats_data = await DatabaseQueries.get_system_stats(session, chain_id)
                if not stats_data:
                    return SystemStats(
                        total_auctions=0,
                        active_auctions=0,
                        unique_tokens=0,
                        total_rounds=0,
                        total_takes=0,
                        total_participants=0
                    )
                
                return SystemStats(
                    total_auctions=stats_data.total_auctions or 0,
                    active_auctions=stats_data.active_auctions or 0,
                    unique_tokens=stats_data.unique_tokens or 0,
                    total_rounds=stats_data.total_rounds or 0,
                    total_takes=stats_data.total_sales or 0,  # Using sales as takes count
                    total_participants=stats_data.total_participants or 0
                )
        except Exception as e:
            logger.error(f"Database error in get_system_stats: {e}")
            raise Exception(f"Failed to fetch system stats from database: {e}")

# Data service factory
def get_data_provider() -> DataProvider:
    """Get the appropriate data provider based on configuration"""
    try:
        from config import get_settings
        settings = get_settings()
        
        # Check if we have a valid database URL  
        database_url = settings.get_effective_database_url()
        if database_url:
            logger.info(f"Using DatabaseDataProvider with database: {database_url}")
            return DatabaseDataProvider()
        else:
            logger.info("No database URL configured, using MockDataProvider")
            return MockDataProvider()
    except ImportError:
        # Fallback to mock if config is not available
        logger.warning("Config not available, using MockDataProvider")
        return MockDataProvider()


if __name__ == "__main__":
    # Test database connection
    async def test_connection():
        success = await init_database()
        if success:
            async with AsyncSessionLocal() as session:
                stats = await DatabaseQueries.get_system_stats(session)
                logger.info(f"System stats: {dict(stats) if stats else 'No data yet'}")
                
                # Test the query methods
                all_auctions = await DatabaseQueries.get_auctions(session, active_only=False)
                active_auctions = await DatabaseQueries.get_auctions(session, active_only=True)
                logger.info(f"Total auctions: {len(all_auctions)}, Active auctions: {len(active_auctions)}")
                
                tokens = await DatabaseQueries.get_all_tokens(session)
                logger.info(f"Total tokens: {len(tokens)}")
                
                recent_sales = await DatabaseQueries.get_recent_sales_activity(session, limit=5)
                logger.info(f"Recent sales: {len(recent_sales)}")

    asyncio.run(test_connection())