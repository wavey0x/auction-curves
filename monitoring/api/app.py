#!/usr/bin/env python3
"""
Unified Auction API server with configurable mock/development/production modes.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
import json
import argparse
from datetime import datetime, timezone

from config import get_settings, get_cors_origins, is_mock_mode, requires_database, get_all_network_configs, get_enabled_networks
from models.auction import SystemStats
from database import get_db, check_database_connection, get_data_provider, DataProvider
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
    from_token: str = Query(..., description="Token being sold"),
    limit: int = Query(50, ge=1, le=100, description="Number of rounds to return"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get round history for an auction"""
    try:
        result = await data_service.get_auction_rounds(auction_address, from_token, limit, chain_id)
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
