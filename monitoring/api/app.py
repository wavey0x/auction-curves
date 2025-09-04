#!/usr/bin/env python3
"""
Unified Auction API server with configurable mock/development/production modes.
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import logging
import json
import argparse
import asyncio
import os
import redis
try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None
from datetime import datetime, timezone

from config import get_settings, get_cors_origins, is_mock_mode, requires_database, get_all_network_configs, get_enabled_networks
from models.auction import SystemStats
from models.taker import TakerSummary, TakerDetail, TakerListResponse, TakerTakesResponse
from database import get_db, check_database_connection, get_data_provider, DataProvider
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from routes.status import router as status_router

# Parse command line arguments
parser = argparse.ArgumentParser(description="Auction API Server")
parser.add_argument('--mock', action='store_true', help='Use mock data provider instead of database')
args = parser.parse_args()

# Store provider mode globally  
PROVIDER_MODE = "mock" if args.mock else None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Log startup information
logger.info("=" * 60)
logger.info(f"🚀 Starting Auction API in {settings.app_mode.upper()} mode")
logger.info("=" * 60)
logger.info(f"App Mode: {settings.app_mode}")
logger.info(f"Data Mode: {'mock (--mock flag)' if args.mock else 'database (default)'}")
logger.info(f"API Host: {settings.api_host}:{settings.api_port}")
logger.info(f"CORS Origins: {settings.cors_origins}")

# Database information
database_url = settings.get_effective_database_url()
if PROVIDER_MODE == "mock":
    logger.info("Data Provider: MockDataProvider (forced by --mock flag)")
elif database_url:
    logger.info(f"Database: {database_url}")
    logger.info("Data Provider: DatabaseDataProvider")
else:
    logger.info("Database: No connection string URL configured!")
    logger.info("Data Provider: Will FAIL - database required")

logger.info("=" * 60)

# Create FastAPI app
app = FastAPI(
    title=f"Auction API ({settings.app_mode.value})",
    description=f"API for Auction data - Running in {settings.app_mode.value} mode",
    version="2.0.0",
    docs_url="/api/docs" if not is_mock_mode() else "/docs",
    redoc_url="/api/redoc" if not is_mock_mode() else "/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount status router
app.include_router(status_router)


# Dependency to get data provider
def get_data_service() -> DataProvider:
    """Get data provider instance"""
    return get_data_provider(force_mode=PROVIDER_MODE)


# Startup validation
@app.on_event("startup")
async def startup_event():
    """Validate that the data provider can be initialized properly"""
    logger.info(f"Validating data provider for mode: {PROVIDER_MODE}")
    
    try:
        provider = get_data_provider(force_mode=PROVIDER_MODE)
        
        if PROVIDER_MODE == "real":
            # Additional validation for real mode
            from database import MockDataProvider
            if isinstance(provider, MockDataProvider):
                error_msg = "CRITICAL: Real mode requested but MockDataProvider returned. Database connection failed!"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info("✅ Database provider validated successfully")
        else:
            logger.info("✅ Mock provider initialized successfully")
            
    except Exception as e:
        logger.error(f"❌ Startup validation failed: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint with API status"""
    return {
        "name": "Auction API",
        "version": "2.0.0",
        "mode": settings.app_mode.value,
        "status": "running",
        "mock_mode": is_mock_mode(),
        "requires_database": requires_database(),
        "enabled_networks": get_enabled_networks(),
        "endpoints": {
            "docs": "/api/docs" if not is_mock_mode() else "/docs",
            "health": "/health",
            "auctions": "/auctions",
            "tokens": "/tokens",
            "networks": "/networks",
            "system_stats": "/system/stats"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    status = {
        "status": "healthy",
        "mode": settings.app_mode.value,
        "mock_mode": is_mock_mode(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if requires_database():
        try:
            # TODO: Add actual database health check
            status["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            status["database"] = "unhealthy"
            status["database_error"] = str(e)
            return JSONResponse(status_code=503, content=status)
    else:
        status["database"] = "not_required"
    
    return status


@app.get("/auctions")
async def get_auctions(
    status: str = Query("all", description="Filter by status: all, active, completed"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    chain_id: Optional[int] = Query(None, description="Filter by chain ID"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get paginated list of auctions"""
    try:
        result = await data_service.get_auctions(status, page, limit, chain_id)
        return result
    except Exception as e:
        logger.error(f"Error fetching auctions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auctions")


@app.get("/auctions/{chain_id}/{auction_address}")
async def get_auction_details(
    chain_id: int,
    auction_address: str,
    data_service: DataProvider = Depends(get_data_service)
):
    """Get detailed auction information"""
    try:
        result = await data_service.get_auction_details(auction_address, chain_id)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction details")

@app.get("/auctions/{chain_id}/{auction_address}/takes")
async def get_auction_takes(
    chain_id: int,
    auction_address: str,
    round_id: Optional[int] = Query(None, description="Filter by round ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of takes to return"),
    offset: int = Query(0, ge=0, description="Number of takes to skip for pagination"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get takes for a specific auction"""
    try:
        result = await data_service.get_auction_takes(auction_address, round_id, limit, chain_id, offset)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction takes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction takes")

@app.get("/auctions/{chain_id}/{auction_address}/rounds")
async def get_auction_rounds(
    chain_id: int,
    auction_address: str,
    from_token: Optional[str] = Query(None, description="Token being sold (optional)"),
    round_id: Optional[int] = Query(None, description="Specific round ID to fetch"),
    limit: int = Query(50, ge=1, le=100, description="Number of rounds to return"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get round history for an auction"""
    try:
        result = await data_service.get_auction_rounds(auction_address, from_token, limit, chain_id, round_id)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction rounds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction rounds")


@app.get("/auctions/{chain_id}/{auction_address}/price-history")
async def get_price_history(
    chain_id: int,
    auction_address: str,
    from_token: str = Query(..., description="Token being sold"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history to return")
):
    """Get price history for charting - placeholder endpoint"""
    # TODO: Implement price history tracking
    return {
        "auction": auction_address,
        "from_token": from_token,
        "points": [],
        "duration_hours": hours
    }


@app.get("/tokens")
async def get_tokens(
    data_service: DataProvider = Depends(get_data_service)
):
    """Get all tokens"""
    try:
        result = await data_service.get_tokens()
        return result
    except Exception as e:
        logger.error(f"Error fetching tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tokens")


@app.get("/system/stats")
async def get_system_stats(
    chain_id: Optional[int] = Query(None, description="Filter by chain ID"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get system statistics"""
    try:
        result = await data_service.get_system_stats(chain_id)
        return result
    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system stats")


@app.get("/chains")
async def get_chains():
    """Get chain information and icons"""
    chain_data = {
        1: {
            "chainId": 1,
            "name": "Ethereum Mainnet",
            "shortName": "Ethereum",
            "icon": "https://icons.llamao.fi/icons/chains/rsz_ethereum.jpg",
            "nativeSymbol": "ETH",
            "explorer": "https://etherscan.io"
        },
        137: {
            "chainId": 137,
            "name": "Polygon",
            "shortName": "Polygon", 
            "icon": "https://icons.llamao.fi/icons/chains/rsz_polygon.jpg",
            "nativeSymbol": "MATIC",
            "explorer": "https://polygonscan.com"
        },
        56: {
            "chainId": 56,
            "name": "BNB Smart Chain",
            "shortName": "BSC",
            "icon": "https://icons.llamao.fi/icons/chains/rsz_binance.jpg",
            "nativeSymbol": "BNB",
            "explorer": "https://bscscan.com"
        },
        42161: {
            "chainId": 42161,
            "name": "Arbitrum One",
            "shortName": "Arbitrum",
            "icon": "https://icons.llamao.fi/icons/chains/rsz_arbitrum.jpg",
            "nativeSymbol": "ETH",
            "explorer": "https://arbiscan.io"
        },
        10: {
            "chainId": 10,
            "name": "Optimism",
            "shortName": "Optimism",
            "icon": "https://icons.llamao.fi/icons/chains/rsz_optimism.jpg",
            "nativeSymbol": "ETH",
            "explorer": "https://optimistic.etherscan.io"
        },
        31337: {
            "chainId": 31337,
            "name": "Anvil Local",
            "shortName": "Anvil",
            "icon": "https://icons.llamao.fi/icons/chains/rsz_ethereum.jpg",
            "nativeSymbol": "ETH",
            "explorer": "#"
        }
    }
    
    return {
        "chains": chain_data,
        "count": len(chain_data)
    }


@app.get("/networks")
async def get_networks():
    """Get active network configurations and their status"""
    try:
        enabled_networks = get_enabled_networks()
        network_configs = get_all_network_configs()
        
        networks = {}
        for network_name in enabled_networks:
            if network_name in network_configs:
                config = network_configs[network_name]
                
                # Determine network status
                status = "configured"
                if is_mock_mode():
                    status = "mock"
                elif not config.get("rpc_url"):
                    status = "missing_rpc"
                elif not config.get("factory_address"):
                    status = "missing_factory"
                else:
                    status = "ready"
                
                networks[network_name] = {
                    "name": config["name"],
                    "short_name": config["short_name"],
                    "chain_id": config["chain_id"],
                    "status": status,
                    "explorer": config["explorer"],
                    "icon": config["icon"],
                    "rpc_configured": bool(config.get("rpc_url")),
                    "factory_configured": bool(config.get("factory_address")),
                    "start_block": config.get("start_block", 0)
                }
        
        return {
            "networks": networks,
            "count": len(networks),
            "mode": settings.app_mode.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching network configurations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch network configurations")


@app.get("/networks/{network_name}")
async def get_network_details(network_name: str):
    """Get detailed information about a specific network"""
    try:
        if network_name not in get_enabled_networks():
            raise HTTPException(status_code=404, detail=f"Network '{network_name}' is not enabled")
        
        network_configs = get_all_network_configs()
        if network_name not in network_configs:
            raise HTTPException(status_code=404, detail=f"Network '{network_name}' configuration not found")
        
        config = network_configs[network_name]
        
        # Determine detailed status
        status_details = {
            "overall": "ready",
            "rpc_status": "configured" if config.get("rpc_url") else "missing",
            "factory_status": "configured" if config.get("factory_address") else "missing",
        }
        
        if is_mock_mode():
            status_details["overall"] = "mock"
            status_details["rpc_status"] = "mock"
            status_details["factory_status"] = "mock"
        elif not config.get("rpc_url") or not config.get("factory_address"):
            status_details["overall"] = "incomplete"
        
        return {
            "network": network_name,
            "name": config["name"],
            "short_name": config["short_name"],
            "chain_id": config["chain_id"],
            "explorer": config["explorer"],
            "icon": config["icon"],
            "rpc_url": config.get("rpc_url", "not_configured"),
            "factory_address": config.get("factory_address", "not_configured"),
            "start_block": config.get("start_block", 0),
            "status": status_details,
            "mode": settings.app_mode.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching network '{network_name}' details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch network details")


@app.get("/chains/{chain_id}")
async def get_chain(chain_id: int):
    """Get specific chain information"""
    chains_response = await get_chains()
    chain_data = chains_response["chains"]
    
    chain = chain_data.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return chain


# Taker endpoints for analyzing wallet/bot behavior
@app.get("/takers")
async def get_takers(
    sort_by: str = Query("volume", regex="^(volume|takes|recent)$", description="Sort by volume, takes count, or most recent activity"),
    limit: int = Query(25, le=100, ge=1, description="Number of takers to return"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    chain_id: Optional[int] = Query(None, description="Filter by specific chain ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    List takers ranked by activity metrics.
    
    - **sort_by**: volume (USD), takes (count), or recent (last activity)
    - **limit**: Number of results per page (max 100)
    - **page**: Page number for pagination
    - **chain_id**: Optional filter by chain ID
    """
    try:
        from database import DatabaseQueries
        
        result = await DatabaseQueries.get_takers_summary(db, sort_by, limit, page, chain_id)
        return result
    except Exception as e:
        logger.error(f"Error fetching takers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch takers: {str(e)}")


@app.get("/takers/{taker_address}")
async def get_taker_details(
    taker_address: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific taker including rankings and auction breakdown.
    
    - **taker_address**: Ethereum address of the taker wallet
    """
    try:
        from database import DatabaseQueries
        
        result = await DatabaseQueries.get_taker_details(db, taker_address)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching taker details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch taker details: {str(e)}")


@app.get("/takers/{taker_address}/takes")
async def get_taker_takes(
    taker_address: str,
    limit: int = Query(20, le=100, ge=1, description="Number of takes to return"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of takes for a specific taker.
    
    - **taker_address**: Ethereum address of the taker wallet
    - **limit**: Number of takes per page (max 100)
    - **page**: Page number for pagination
    """
    try:
        from database import DatabaseQueries
        
        result = await DatabaseQueries.get_taker_takes(db, taker_address, limit, page)
        return result
    except Exception as e:
        logger.error(f"Error fetching taker takes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch taker takes: {str(e)}")

@app.get("/takers/{taker_address}/token-pairs", tags=["Takers"])
async def get_taker_token_pairs(
    taker_address: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Number of token pairs per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most frequented token pairs for a specific taker.
    
    Shows the from_token -> to_token pairs ranked by frequency of takes.
    
    - **taker_address**: Ethereum address of the taker wallet
    - **page**: Page number (starts at 1)
    - **limit**: Number of token pairs per page
    """
    try:
        from database import DatabaseQueries
        
        result = await DatabaseQueries.get_taker_token_pairs(db, taker_address, page, limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching taker token pairs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch taker token pairs: {str(e)}")


# Take Details endpoints
@app.get("/takes/{chain_id}/{auction_address}/{round_id}/{take_seq}")
async def get_take_details(
    chain_id: int,
    auction_address: str,
    round_id: int,
    take_seq: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive take details including price analysis from multiple sources.
    
    Parameters:
    - chain_id: Chain ID where the take occurred
    - auction_address: Auction contract address
    - round_id: Round ID within the auction
    - take_seq: Take sequence number within the round
    
    Returns detailed take information with:
    - Core take data (amounts, tokens, transaction details)
    - Gas costs and transaction fees  
    - Price quotes from multiple sources (YPM, Enso, Odos, CowSwap)
    - PnL analysis based on price variations
    - Auction and round context
    """
    try:
        # Import here to avoid circular import issues
        from database import DatabaseQueries
        
        # Get take details with price quotes
        raw_data = await DatabaseQueries.get_take_details(db, auction_address, round_id, take_seq, chain_id)
        
        if not raw_data:
            raise HTTPException(status_code=404, detail=f"Take {auction_address}-{round_id}-{take_seq} not found on chain {chain_id}")
            
        take_data = raw_data["take_data"]
        price_quotes = raw_data["price_quotes"]
        round_context = raw_data["round_context"]
        
        # Transform price quotes into PriceQuote objects
        quotes_by_token = {}
        for quote in price_quotes:
            token_addr = quote.token_address.lower()
            if token_addr not in quotes_by_token:
                quotes_by_token[token_addr] = []
            
            quotes_by_token[token_addr].append({
                "source": quote.source,
                "token_address": quote.token_address,
                "token_symbol": quote.token_symbol,
                "price_usd": float(quote.price_usd),
                "block_number": quote.block_number,
                "timestamp": quote.timestamp,
                "block_distance": quote.block_distance,
                "time_distance": quote.time_distance
            })
        
        # Calculate PnL analysis
        from_token_quotes = quotes_by_token.get(take_data.from_token.lower(), [])
        to_token_quotes = quotes_by_token.get(take_data.to_token.lower(), [])
        
        # Base calculation using primary prices (closest to take)
        from_price = float(take_data.from_token_price_usd) if take_data.from_token_price_usd else 0.0
        to_price = float(take_data.to_token_price_usd) if take_data.to_token_price_usd else 0.0
        amount_taken = float(take_data.amount_taken)
        amount_paid = float(take_data.amount_paid)
        
        base_take_value = amount_taken * from_price
        
        # Calculate PnL for different price combinations
        pnl_scenarios = []
        if from_token_quotes and to_token_quotes:
            for from_quote in from_token_quotes:
                for to_quote in to_token_quotes:
                    scenario_value = amount_taken * from_quote["price_usd"]
                    cost_value = amount_paid * to_quote["price_usd"]
                    pnl = scenario_value - cost_value
                    pnl_scenarios.append(pnl)
        
        # PnL analysis
        base_pnl = base_take_value - (amount_paid * to_price) if to_price > 0 else 0.0
        best_case_pnl = max(pnl_scenarios) if pnl_scenarios else base_pnl
        worst_case_pnl = min(pnl_scenarios) if pnl_scenarios else base_pnl
        average_pnl = sum(pnl_scenarios) / len(pnl_scenarios) if pnl_scenarios else base_pnl
        
        # Calculate price variance
        all_from_prices = [q["price_usd"] for q in from_token_quotes]
        price_variance = 0.0
        if len(all_from_prices) > 1:
            price_mean = sum(all_from_prices) / len(all_from_prices)
            price_variance = (max(all_from_prices) - min(all_from_prices)) / price_mean * 100
            
        # Build response
        response = {
            # Core take data
            "take_id": take_data.take_id,
            "auction_address": take_data.auction_address,
            "chain_id": take_data.chain_id,
            "round_id": take_data.round_id,
            "take_seq": take_data.take_seq,
            "taker": take_data.taker,
            
            # Token exchange details
            "from_token": take_data.from_token,
            "to_token": take_data.to_token,
            "from_token_symbol": take_data.from_token_symbol,
            "to_token_symbol": take_data.to_token_symbol,
            "amount_taken": str(take_data.amount_taken),
            "amount_paid": str(take_data.amount_paid),
            "price": str(take_data.price),
            
            # Transaction details
            "tx_hash": take_data.transaction_hash,
            "block_number": take_data.block_number,
            "timestamp": take_data.timestamp.isoformat() if hasattr(take_data.timestamp, 'isoformat') else str(take_data.timestamp),
            
            # Gas costs
            "gas_price": float(take_data.gas_price) if take_data.gas_price else None,
            "base_fee": float(take_data.base_fee) if take_data.base_fee else None,
            "priority_fee": float(take_data.priority_fee) if take_data.priority_fee else None,
            "gas_used": int(take_data.gas_used) if take_data.gas_used else None,
            "transaction_fee_eth": float(take_data.transaction_fee_eth) if take_data.transaction_fee_eth else None,
            "transaction_fee_usd": float(take_data.transaction_fee_usd) if take_data.transaction_fee_usd else None,
            
            # Price quotes from different sources
            "price_quotes": [q for quotes in quotes_by_token.values() for q in quotes],
            
            # PnL analysis
            "pnl_analysis": {
                "base_pnl": base_pnl,
                "best_case_pnl": best_case_pnl,
                "worst_case_pnl": worst_case_pnl,
                "average_pnl": average_pnl,
                "price_variance_percent": price_variance,
                "take_value_usd": base_take_value
            },
            
            # Auction context
            "auction_decay_rate": float(take_data.auction_decay_rate) if take_data.auction_decay_rate else None,
            "auction_update_interval": int(take_data.auction_update_interval) if take_data.auction_update_interval else None,
            "round_total_takes": int(round_context.total_takes) if round_context else None,
            "round_available_before": str(round_context.available_amount) if round_context else None,
            "round_available_after": str(round_context.available_amount) if round_context else None
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching take details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch take details: {str(e)}")


# Legacy endpoints for backwards compatibility
@app.get("/activity/kicks")
async def legacy_get_kicks(limit: int = Query(50, ge=1, le=100)):
    """Legacy kicks endpoint - placeholder for backwards compatibility"""
    return {
        "events": [],
        "count": 0,
        "has_more": False
    }


@app.get("/activity/takes") 
async def get_recent_takes(
    limit: int = Query(50, ge=1, le=500),
    chain_id: Optional[int] = Query(None, description="Filter by chain ID"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Recent takes across all auctions (most recent first)"""
    try:
        takes = await data_service.get_recent_takes(limit, chain_id)
        return takes
    except Exception as e:
        logger.error(f"Error fetching recent takes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent takes")


@app.get("/analytics/overview")
async def get_system_overview(
    data_service: DataProvider = Depends(get_data_service)
):
    """Get system overview with legacy format"""
    try:
        stats = await data_service.get_system_stats()
        return {
            "system_stats": stats.dict(),
            "activity": {
                "rounds_kicked_24h": 12,
                "avg_sales_per_round": 5.0
            },
            "health": {
                "database_connected": True,
                "indexing_active": not is_mock_mode()
            }
        }
    except Exception as e:
        logger.error(f"Error fetching system overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system overview")


# Event Stream endpoint for real-time notifications
@app.get("/events/stream")
async def event_stream(
    request: Request,
    from_id: str = Query(None, alias="from", description="Start from specific stream ID"),
    types: str = Query(None, description="Comma-separated event types to filter (kick,take,deploy)"),
    max_replay: int = Query(100, description="Maximum number of events to replay on reconnect")
):
    """Server-Sent Events endpoint for real-time event notifications"""
    
    async def simple_event_generator():
        try:
            # Send initial connection event
            yield "data: {\"type\": \"connected\"}\n\n"
            
            # Build Redis client (prefer asyncio to avoid blocking the event loop)
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            use_async = aioredis is not None
            if use_async:
                redis_client = aioredis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                )
                await redis_client.ping()
            else:
                # Fallback to synchronous client, we will run blocking calls in a thread
                redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                    socket_keepalive=True,
                    socket_keepalive_options={}
                )
                # Probe connection without blocking the event loop
                await asyncio.to_thread(redis_client.ping)
            logger.info("SSE: Redis connected successfully")
            
            # Send recent unseen events that aren't too old
            try:
                # Get current time for age calculations
                import time
                current_time_ms = int(time.time() * 1000)
                
                # Get from_id from query param or Last-Event-ID header for resume capability
                start_from = request.query_params.get('from') or request.headers.get("Last-Event-ID", None)
                
                # Check if start_from is too old (> 5 minutes) and ignore if so
                if start_from:
                    try:
                        event_time_ms = int(start_from.split('-')[0])
                        age_ms = current_time_ms - event_time_ms
                        if age_ms > (5 * 60 * 1000):  # 5 minutes
                            logger.info(f"SSE: Ignoring old start_from ({age_ms/1000:.1f}s old), starting fresh")
                            start_from = None
                    except (ValueError, IndexError):
                        logger.warn(f"SSE: Invalid start_from format '{start_from}', starting fresh")
                        start_from = None
                
                # Only send historical events if no resume point (new connection)
                if not start_from:
                    if use_async:
                        recent_messages = await redis_client.xrevrange('events', count=10)  # type: ignore
                    else:
                        recent_messages = await asyncio.to_thread(redis_client.xrevrange, 'events', None, None, 10)
                    
                    # Filter for recent events (last 5 minutes)
                    five_minutes_ago = current_time_ms - (5 * 60 * 1000)
                    
                    filtered_events = []
                    for message_id, data in recent_messages:
                        try:
                            # Extract timestamp from Redis Stream ID format: timestamp-sequence
                            event_time_ms = int(message_id.split('-')[0])
                            if event_time_ms > five_minutes_ago:
                                filtered_events.append((message_id, data))
                        except (ValueError, IndexError):
                            # Invalid message ID format, skip
                            continue
                    
                    # Send only the 5 most recent valid events
                    events_to_send = list(reversed(filtered_events[-5:]))  # Oldest first
                    
                    if events_to_send:
                        logger.info(f"SSE: Sending {len(events_to_send)} recent unseen events (last 5 min)")
                        for message_id, data in events_to_send:
                            try:
                                processed_data = dict(data)
                                if 'payload_json' in processed_data and processed_data['payload_json']:
                                    if processed_data['payload_json'] != 'undefined':
                                        processed_data['payload_json'] = json.loads(processed_data['payload_json'])
                                
                                event_data = json.dumps(processed_data)
                                yield f"id: {message_id}\n"
                                yield f"data: {event_data}\n\n"
                                await asyncio.sleep(0.1)  # Small delay between events
                            except Exception as e:
                                logger.error(f"SSE: Error processing message {message_id}: {e}")
                    else:
                        logger.info("SSE: No recent events to send (none in last 5 minutes)")
                else:
                    logger.info(f"SSE: Resuming from event ID {start_from}, skipping historical events")
                    
            except Exception as e:
                logger.error(f"SSE: Error getting recent events: {e}")
            
            # Now poll for new events in real-time
            current_id = "$"  # Start from new events only
            heartbeat_count = 0
            
            while True:
                try:
                    # Use XREAD to get new events from the stream
                    messages = await _xread_messages(redis_client, current_id)
                    
                    if messages:
                        for stream_name, stream_messages in messages:
                            for message_id, data in stream_messages:
                                try:
                                    processed_data = dict(data)
                                    if 'payload_json' in processed_data and processed_data['payload_json']:
                                        if processed_data['payload_json'] != 'undefined':
                                            processed_data['payload_json'] = json.loads(processed_data['payload_json'])
                                    
                                    event_data = json.dumps(processed_data)
                                    yield f"id: {message_id}\n"
                                    yield f"data: {event_data}\n\n"
                                    
                                    current_id = message_id
                                except Exception as e:
                                    logger.error(f"SSE: Error processing new event {message_id}: {e}")
                                    current_id = message_id
                    else:
                        # No new messages, send heartbeat every 10 polling cycles (20 seconds)
                        heartbeat_count += 1
                        if heartbeat_count % 10 == 0:
                            yield ": heartbeat\n\n"
                            
                except redis.TimeoutError:
                    # Redis XREAD timeout is normal, just continue polling
                    continue
                except redis.ConnectionError:
                    logger.error("SSE: Redis connection lost during polling")
                    break
                except Exception as e:
                    logger.error(f"SSE: Error during event polling: {e}")
                    # Don't break on unexpected errors, just continue
                    await asyncio.sleep(1)  # Brief pause before retrying
                    continue
                    
        except Exception as e:
            logger.error(f"SSE: Error in simple generator: {e}")
            yield f"data: {{\"type\": \"error\", \"message\": \"Error: {str(e)}\"}}\n\n"
        finally:
            try:
                # Properly close async client
                if 'redis_client' in locals() and aioredis is not None and isinstance(redis_client, aioredis.Redis):  # type: ignore
                    await redis_client.close()  # type: ignore
            except Exception:
                pass

    # Inner loop for polling new messages, implemented twice to avoid blocking
    async def _xread_messages(redis_client, current_id):
        if aioredis is not None and isinstance(redis_client, aioredis.Redis):  # type: ignore
            return await redis_client.xread({'events': current_id}, count=10, block=2000)  # type: ignore
        # Fallback: run sync xread in a thread to avoid blocking the event loop
        return await asyncio.to_thread(redis_client.xread, {'events': current_id}, 10, 2000)

    return StreamingResponse(
        simple_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Last-Event-ID,Cache-Control",
            "Access-Control-Expose-Headers": "Last-Event-ID"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Auction API in {settings.app_mode.value} mode")
    logger.info(f"Mock mode: {is_mock_mode()}")
    logger.info(f"Requires database: {requires_database()}")
    
    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
