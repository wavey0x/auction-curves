#!/usr/bin/env python3
"""
Database connection and session management for FastAPI.
"""

import os
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
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
# Only enable SQL logging in debug mode (set SQL_DEBUG=true to enable)
sql_debug = os.getenv("SQL_DEBUG", "false").lower() == "true"
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=sql_debug,  # Enable SQL logging only when SQL_DEBUG=true
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
        chain_filter = "AND chain_id = :chain_id" if chain_id else ""
        
        if active_only:
            query = text(f"""
                SELECT vw.*, a.decay_rate
                FROM vw_auctions vw
                JOIN auctions a ON vw.auction_address = a.auction_address AND vw.chain_id = a.chain_id
                WHERE vw.has_active_round = TRUE
                {chain_filter}
                ORDER BY vw.last_kicked DESC NULLS LAST
            """)
        else:
            query = text(f"""
                SELECT vw.*, a.decay_rate
                FROM vw_auctions vw
                JOIN auctions a ON vw.auction_address = a.auction_address AND vw.chain_id = a.chain_id
                WHERE 1=1
                {chain_filter}
                ORDER BY vw.last_kicked DESC NULLS LAST
            """)
        
        params = {"chain_id": chain_id} if chain_id else {}
        result = await db.execute(query, params)
        return result.fetchall()
    
    @staticmethod
    async def get_auction_details(db: AsyncSession, auction_address: str, chain_id: int = None):
        """Get detailed information about a specific Auction"""
        chain_filter = "AND vw.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT vw.*, a.timestamp as deployed_timestamp, a.decay_rate
            FROM vw_auctions vw
            JOIN auctions a ON vw.auction_address = a.auction_address AND vw.chain_id = a.chain_id
            WHERE LOWER(vw.auction_address) = LOWER(:auction_address)
            {chain_filter}
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
                ahp.auction_length
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
    async def get_auction_takes(db: AsyncSession, auction_address: str, round_id: int = None, chain_id: int = None, limit: int = 50, offset: int = 0):
        """Get takes history for an Auction using enhanced vw_takes view with USD prices"""
        chain_filter = "AND chain_id = :chain_id" if chain_id else ""
        round_filter = "AND round_id = :round_id" if round_id else ""
        
        query = text(f"""
            SELECT 
                take_id,
                auction_address,
                chain_id,
                round_id,
                take_seq,
                taker,
                from_token,
                to_token,
                amount_taken,
                amount_paid,
                price,
                timestamp,
                seconds_from_round_start,
                block_number,
                transaction_hash,
                log_index,
                round_kicked_at,
                from_symbol,
                from_name,
                from_decimals,
                to_symbol,
                to_name,
                to_decimals,
                from_token_price_usd,
                want_token_price_usd,
                amount_taken_usd,
                amount_paid_usd,
                price_differential_usd,
                price_differential_percent
            FROM vw_takes
            WHERE LOWER(auction_address) = LOWER(:auction_address)
            {chain_filter}
            {round_filter}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params = {
            "auction_address": auction_address,
            "limit": limit,
            "offset": offset
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
        """Get overall system statistics using optimized subqueries"""
        chain_filter = "WHERE chain_id = :chain_id" if chain_id else ""
        auction_filter = "WHERE auction_address IN (SELECT auction_address FROM auctions" + (f" WHERE chain_id = :chain_id)" if chain_id else ")")
        
        query = text(f"""
            SELECT 
                (SELECT COUNT(*) FROM auctions {chain_filter}) as total_auctions,
                (SELECT COUNT(DISTINCT auction_address) FROM rounds {auction_filter} AND round_end > EXTRACT(EPOCH FROM NOW())::BIGINT AND available_amount > 0) as active_auctions,
                (SELECT COUNT(DISTINCT address) FROM tokens {chain_filter}) as unique_tokens,
                (SELECT COUNT(*) FROM rounds {auction_filter}) as total_rounds,
                (SELECT COUNT(*) FROM takes {auction_filter}) as total_takes,
                (SELECT COUNT(DISTINCT taker) FROM takes {auction_filter}) as total_participants
        """)
        
        params = {"chain_id": chain_id} if chain_id else {}
        result = await db.execute(query, params)
        return result.fetchone()
    
    @staticmethod
    async def get_recent_takes_activity(db: AsyncSession, limit: int = 25, chain_id: int = None):
        """Get recent takes activity across all Auctions"""
        chain_filter = "WHERE als.chain_id = :chain_id" if chain_id else ""
        
        query = text(f"""
            SELECT 
                als.take_id as id,
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
                als.take_seq
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
        chain_id: int = None,
        offset: int = 0
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
            is_active=True,  # Mock data - would be calculated in real implementation
            current_price="950000",
            available_amount="800000000000000000000",
            time_remaining=1800,
            seconds_elapsed=1800,
            total_takes=5,
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
                total_takes=5,
                recent_takes=[]
            ),
            deployed_at=datetime.now() - timedelta(days=30),
            last_kicked=datetime.now() - timedelta(minutes=30)
        )

    async def get_auction_takes(self, auction_address: str, round_id: Optional[int] = None, limit: int = 50, chain_id: int = None, offset: int = 0) -> List[Take]:
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
            total_takes=100
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
                        "want_token": {"address": auction_row.want_token, "symbol": getattr(auction_row, 'want_token_symbol', None) or "Unknown", "name": getattr(auction_row, 'want_token_name', None) or "Unknown", "decimals": getattr(auction_row, 'want_token_decimals', None) or 18, "chain_id": auction_row.chain_id},
                        "current_round": (
                            {
                                "round_id": getattr(auction_row, 'current_round_id', None),
                                "round_start": getattr(auction_row, 'round_start', None),
                                "round_end": getattr(auction_row, 'round_end', None),
                                "is_active": getattr(auction_row, 'has_active_round', False),
                                "total_takes": getattr(auction_row, 'current_round_takes', 0) if hasattr(auction_row, 'current_round_takes') else 0
                            }
                            if getattr(auction_row, 'current_round_id', None) else None
                        ),
                        "last_kicked": datetime.fromtimestamp(auction_row.last_kicked, tz=timezone.utc) if getattr(auction_row, 'last_kicked', None) else None,
                        "decay_rate": float(getattr(auction_row, 'decay_rate')) if getattr(auction_row, 'decay_rate', None) is not None else None,
                        "update_interval": getattr(auction_row, 'price_update_interval', None)
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

                # Use actual database data from vw_auctions
                want_token = TokenInfo(
                    address=auction_data.want_token,
                    symbol=getattr(auction_data, 'want_token_symbol', None) or "Unknown",
                    name=getattr(auction_data, 'want_token_name', None) or "Unknown", 
                    decimals=getattr(auction_data, 'want_token_decimals', None) or 18,
                    chain_id=chain_id
                )

                parameters = AuctionParameters(
                    price_update_interval=int(getattr(auction_data, 'price_update_interval', 60) or 60),
                    step_decay=None,
                    step_decay_rate=str(getattr(auction_data, 'step_decay_rate')) if getattr(auction_data, 'step_decay_rate', None) is not None else None,
                    decay_rate=float(getattr(auction_data, 'decay_rate')) if getattr(auction_data, 'decay_rate', None) is not None else None,
                    auction_length=int(getattr(auction_data, 'auction_length', 0) or 0),
                    starting_price=str(getattr(auction_data, 'starting_price')) if getattr(auction_data, 'starting_price', None) is not None else "0"
                )
                
                current_round = None
                if getattr(auction_data, 'has_active_round', False) and getattr(auction_data, 'current_round_id', None):
                    current_round = AuctionRoundInfo(
                        round_id=getattr(auction_data, 'current_round_id'),
                        kicked_at=datetime.fromtimestamp(getattr(auction_data, 'last_kicked')) if getattr(auction_data, 'last_kicked', None) else datetime.now(),
                        round_start=getattr(auction_data, 'round_start', None),
                        round_end=getattr(auction_data, 'round_end', None),
                        initial_available=str(getattr(auction_data, 'current_available', 0) or 0),
                        is_active=getattr(auction_data, 'has_active_round', False),
                        available_amount=str(getattr(auction_data, 'current_available', 0) or 0),
                        seconds_elapsed=0,  # Can be calculated on frontend if needed
                        total_takes=getattr(auction_data, 'current_round_takes', 0) or 0,
                        progress_percentage=getattr(auction_data, 'progress_percentage', 0.0) or 0.0
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
                    deployed_at=datetime.fromtimestamp(getattr(auction_data, 'deployed_timestamp', 0), tz=timezone.utc) if getattr(auction_data, 'deployed_timestamp', None) else datetime.now(tz=timezone.utc),
                    last_kicked=datetime.fromtimestamp(getattr(auction_data, 'last_kicked')) if getattr(auction_data, 'last_kicked', None) else None
                )
        except Exception as e:
            logger.error(f"Database error in get_auction_details: {e}")
            raise Exception(f"Failed to fetch auction details from database: {e}")

    async def get_auction_takes(self, auction_address: str, round_id: Optional[int] = None, limit: int = 50, chain_id: int = None, offset: int = 0) -> List[Take]:
        """Get takes from database"""
        try:
            async with AsyncSessionLocal() as session:
                # Use the proper method name for takes
                takes_data = await DatabaseQueries.get_auction_takes(
                    session, auction_address, round_id, chain_id, limit, offset
                )
                
                takes = []
                for take_row in takes_data:
                    take = Take(
                        take_id=str(take_row.take_id) if take_row.take_id else f"take_{take_row.take_seq}",
                        auction=take_row.auction_address,
                        chain_id=take_row.chain_id,
                        round_id=take_row.round_id,
                        take_seq=take_row.take_seq,
                        taker=take_row.taker,
                        amount_taken=str(take_row.amount_taken),
                        amount_paid=str(take_row.amount_paid),
                        price=str(take_row.price),
                        timestamp=take_row.timestamp.isoformat() if hasattr(take_row.timestamp, 'isoformat') else str(take_row.timestamp),
                        tx_hash=take_row.transaction_hash,
                        block_number=take_row.block_number,
                        # Add token information
                        from_token=take_row.from_token,
                        to_token=take_row.to_token,
                        from_token_symbol=getattr(take_row, 'from_symbol', None),
                        from_token_name=getattr(take_row, 'from_name', None),
                        from_token_decimals=getattr(take_row, 'from_decimals', None),
                        to_token_symbol=getattr(take_row, 'to_symbol', None),
                        to_token_name=getattr(take_row, 'to_name', None),
                        to_token_decimals=getattr(take_row, 'to_decimals', None),
                        # Add USD price information
                        from_token_price_usd=str(take_row.from_token_price_usd) if getattr(take_row, 'from_token_price_usd', None) is not None else None,
                        want_token_price_usd=str(take_row.want_token_price_usd) if getattr(take_row, 'want_token_price_usd', None) is not None else None,
                        amount_taken_usd=str(take_row.amount_taken_usd) if getattr(take_row, 'amount_taken_usd', None) is not None else None,
                        amount_paid_usd=str(take_row.amount_paid_usd) if getattr(take_row, 'amount_paid_usd', None) is not None else None,
                        price_differential_usd=str(take_row.price_differential_usd) if getattr(take_row, 'price_differential_usd', None) is not None else None,
                        price_differential_percent=float(take_row.price_differential_percent) if getattr(take_row, 'price_differential_percent', None) is not None else None
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
                        (ar.round_end > EXTRACT(EPOCH FROM NOW())::BIGINT AND ar.available_amount > 0) as is_active,
                        ar.total_takes
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
                        "round_start": round_row.round_start if hasattr(round_row, 'round_start') and round_row.round_start else round_row.kicked_at,
                        "round_end": round_row.round_end if hasattr(round_row, 'round_end') and round_row.round_end else None,
                        "initial_available": str(round_row.initial_available) if round_row.initial_available else "0",
                        "is_active": round_row.is_active or False,
                        "total_takes": round_row.total_takes or 0
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
                    total_takes=stats_data.total_takes or 0,
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
                
                recent_takes = await DatabaseQueries.get_recent_takes_activity(session, limit=5)
                logger.info(f"Recent takes: {len(recent_takes)}")

    asyncio.run(test_connection())
