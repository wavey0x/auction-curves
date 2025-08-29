#!/usr/bin/env python3
"""
Unified Auction API server with configurable mock/development/production modes.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone

from config import get_settings, get_cors_origins, is_mock_mode, requires_database, get_all_network_configs, get_enabled_networks
from services.data_service import get_data_provider, DataProvider
from models.auction import SystemStats
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

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
    return get_data_provider()


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


@app.get("/auctions/{auction_address}")
async def get_auction_details(
    auction_address: str,
    data_service: DataProvider = Depends(get_data_service)
):
    """Get detailed auction information"""
    try:
        result = await data_service.get_auction_details(auction_address)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction details")


@app.get("/auctions/{auction_address}/sales")
async def get_auction_sales(
    auction_address: str,
    round_id: Optional[int] = Query(None, description="Filter by round ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of sales to return"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get sales for a specific auction"""
    try:
        result = await data_service.get_auction_sales(auction_address, round_id, limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction sales: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction sales")


@app.get("/auctions/{auction_address}/rounds")
async def get_auction_rounds(
    auction_address: str,
    from_token: str = Query(..., description="Token being sold"),
    limit: int = Query(50, ge=1, le=100, description="Number of rounds to return"),
    data_service: DataProvider = Depends(get_data_service)
):
    """Get round history for an auction"""
    try:
        result = await data_service.get_auction_rounds(auction_address, from_token, limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching auction rounds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch auction rounds")


@app.get("/auctions/{auction_address}/price-history")
async def get_price_history(
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
async def legacy_get_takes(limit: int = Query(50, ge=1, le=100)):
    """Legacy takes endpoint - placeholder for backwards compatibility"""
    return {
        "events": [],
        "count": 0,
        "has_more": False
    }


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


# Webhook endpoints for Rindexer custom business logic
@app.post("/webhook/process-event")
async def process_rindexer_event(event_data: dict):
    """Process events from Rindexer streams for custom business logic"""
    try:
        event_type = event_data.get("event_name")
        logger.info(f"Processing webhook event: {event_type}")
        
        if event_type == "AuctionKicked":
            await handle_auction_kicked(event_data)
        elif event_type == "AuctionSale" or event_type.endswith("_sale"):
            await handle_auction_sale(event_data)
        elif event_type == "DeployedNewAuction":
            await handle_new_auction_deployed(event_data)
        elif event_type == "AuctionEnabled":
            await handle_auction_enabled(event_data)
        elif event_type == "AuctionDisabled":
            await handle_auction_disabled(event_data)
        elif event_type == "UpdatedStartingPrice":
            await handle_updated_starting_price(event_data)
        elif event_type == "UpdatedStepDecayRate":
            await handle_updated_step_decay_rate(event_data)
        else:
            logger.warning(f"Unhandled event type: {event_type}")
        
        return {"status": "processed", "event_type": event_type}
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook event")


async def handle_auction_kicked(event_data: dict):
    """Handle AuctionKicked events - increment round counter and fetch prices"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        from_token = event_data.get("from_token")
        to_token = event_data.get("to_token")
        block_number = event_data.get("block_number")
        
        if not auction_address:
            logger.warning("No auction address in AuctionKicked event")
            return
        
        # Auto-increment round ID per auction
        await increment_auction_round(auction_address, event_data)
        
        # Fetch token prices at kick time if we have token addresses
        if from_token and block_number:
            await fetch_and_store_token_price(from_token, block_number)
        if to_token and block_number:
            await fetch_and_store_token_price(to_token, block_number)
            
        logger.info(f"Processed AuctionKicked for {auction_address}")
    except Exception as e:
        logger.error(f"Error handling AuctionKicked: {e}")


async def handle_auction_sale(event_data: dict):
    """Handle sale/take events - record sale and update round statistics"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        amount_taken = event_data.get("amount_taken", event_data.get("amount"))
        amount_paid = event_data.get("amount_paid", "0")
        price = event_data.get("price", "0")
        taker = event_data.get("taker", event_data.get("buyer"))
        from_token = event_data.get("from_token")
        to_token = event_data.get("to_token")
        chain_id = event_data.get("chain_id", 31337)
        block_number = event_data.get("block_number", 0)
        transaction_hash = event_data.get("transaction_hash", "")
        log_index = event_data.get("log_index", 0)
        
        if not auction_address or not amount_taken:
            logger.warning("Missing data in sale event")
            return
        
        # Record the sale first
        await record_auction_sale(auction_address, {
            "amount_taken": amount_taken,
            "amount_paid": amount_paid,
            "price": price,
            "taker": taker,
            "from_token": from_token,
            "to_token": to_token,
            "chain_id": chain_id,
            "block_number": block_number,
            "transaction_hash": transaction_hash,
            "log_index": log_index
        })
        
        # Update round statistics
        await update_round_statistics(auction_address, amount_taken)
        
        logger.info(f"Processed sale for {auction_address}: {amount_taken} taken by {taker}")
    except Exception as e:
        logger.error(f"Error handling auction sale: {e}")


async def handle_new_auction_deployed(event_data: dict):
    """Handle new auction deployment - cache contract parameters"""
    try:
        auction_address = event_data.get("auction", event_data.get("auction_address"))
        want_token = event_data.get("want", event_data.get("want_token"))
        factory_address = event_data.get("factory_address", event_data.get("contract_address"))
        contract_name = event_data.get("contract_name", "")
        
        if not auction_address:
            logger.warning("No auction address in DeployedNewAuction event")
            return
        
        # Detect auction version based on factory/contract name
        auction_version = detect_auction_version(factory_address, contract_name)
        
        # Initialize auction parameters cache with version
        await cache_auction_parameters(auction_address, want_token, factory_address, auction_version)
        
        logger.info(f"Processed new {auction_version} auction deployment: {auction_address}")
    except Exception as e:
        logger.error(f"Error handling new auction deployment: {e}")


def detect_auction_version(factory_address: str, contract_name: str) -> str:
    """Detect auction version based on factory address or contract name"""
    try:
        # Check if it's a legacy factory/contract
        if contract_name and "Legacy" in contract_name:
            return "0.0.1"
        
        # Check known legacy factory addresses (add actual deployed addresses here)
        legacy_factories = {
            # Add known legacy factory addresses for each network
            # Example: "0x123...": "0.0.1"
        }
        
        if factory_address and factory_address.lower() in [addr.lower() for addr in legacy_factories.keys()]:
            return "0.0.1"
        
        # Default to new version for unknown factories
        return "0.1.0"
        
    except Exception as e:
        logger.error(f"Error detecting auction version: {e}")
        return "0.1.0"  # Default to new version


async def increment_auction_round(auction_address: str, event_data: dict):
    """Auto-increment round counter per auction address"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would increment round for {auction_address}")
            return
        
        # Extract event data
        from_token = event_data.get("from_token")
        initial_available = event_data.get("initial_available", event_data.get("amount", "0"))
        block_number = event_data.get("block_number", 0)
        transaction_hash = event_data.get("transaction_hash", "")
        chain_id = event_data.get("chain_id", 31337)  # Default to local Anvil
        
        if not from_token:
            logger.warning(f"No from_token in AuctionKicked event for {auction_address}")
            return
            
        # Insert into database
        async for db in get_db():
            try:
                # First, deactivate any previous active rounds for this auction
                deactivate_query = text("""
                    UPDATE auction_rounds 
                    SET is_active = FALSE 
                    WHERE auction_address = :auction_address AND chain_id = :chain_id AND is_active = TRUE
                """)
                
                await db.execute(deactivate_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id
                })
                
                # Get next round ID and insert new round
                insert_query = text("""
                    INSERT INTO auction_rounds (
                        auction_address, chain_id, round_id, from_token,
                        kicked_at, initial_available, is_active,
                        current_price, available_amount, time_remaining, seconds_elapsed,
                        total_sales, total_volume_sold, progress_percentage,
                        block_number, transaction_hash
                    )
                    VALUES (
                        :auction_address, :chain_id, 
                        COALESCE((SELECT MAX(round_id) + 1 FROM auction_rounds WHERE auction_address = :auction_address AND chain_id = :chain_id), 1),
                        :from_token, NOW(), :initial_available, TRUE,
                        0, :initial_available, 3600, 0,
                        0, 0, 0,
                        :block_number, :transaction_hash
                    )
                    RETURNING round_id
                """)
                
                result = await db.execute(insert_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "from_token": from_token,
                    "initial_available": str(initial_available),
                    "block_number": block_number,
                    "transaction_hash": transaction_hash
                })
                
                round_id = result.scalar()
                await db.commit()
                
                logger.info(f"Created round {round_id} for auction {auction_address} with {initial_available} {from_token}")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error incrementing auction round: {db_error}")
                raise
            break  # Exit the async generator after first iteration
                
    except Exception as e:
        logger.error(f"Error incrementing auction round: {e}")


async def fetch_and_store_token_price(token_address: str, block_number: int):
    """Fetch external token price at specific block and store it"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would fetch price for token {token_address} at block {block_number}")
            return
            
        # TODO: Implement external price API integration
        # This would integrate with services like:
        # - Coingecko API for historical prices
        # - DeFiLlama API
        # - Chainlink price feeds
        # - DEX aggregators
        logger.info(f"Would fetch price for token {token_address} at block {block_number}")
    except Exception as e:
        logger.error(f"Error fetching token price: {e}")


async def update_round_statistics(auction_address: str, amount_taken: str):
    """Update round statistics after a sale"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would update stats for {auction_address}, amount: {amount_taken}")
            return
        
        chain_id = 31337  # Default to local Anvil
        
        async for db in get_db():
            try:
                # Update the active round for this auction
                update_query = text("""
                    UPDATE auction_rounds 
                    SET 
                        total_sales = total_sales + 1,
                        total_volume_sold = total_volume_sold + :amount_taken,
                        available_amount = GREATEST(0, available_amount - :amount_taken),
                        progress_percentage = CASE 
                            WHEN initial_available > 0 THEN 
                                LEAST(100, ((initial_available - GREATEST(0, available_amount - :amount_taken)) * 100.0 / initial_available))
                            ELSE 0 
                        END
                    WHERE auction_address = :auction_address 
                      AND chain_id = :chain_id 
                      AND is_active = TRUE
                    RETURNING round_id, total_sales, progress_percentage
                """)
                
                result = await db.execute(update_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "amount_taken": str(amount_taken)
                })
                
                row = result.fetchone()
                if row:
                    round_id, total_sales, progress = row
                    await db.commit()
                    logger.info(f"Updated round {round_id} for {auction_address}: {total_sales} sales, {progress:.2f}% progress")
                else:
                    logger.warning(f"No active round found for auction {auction_address}")
                    
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error updating round statistics: {db_error}")
                raise
            break  # Exit the async generator after first iteration
            
    except Exception as e:
        logger.error(f"Error updating round statistics: {e}")


async def record_auction_sale(auction_address: str, sale_data: dict):
    """Record a sale in the auction_sales table"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would record sale for {auction_address}")
            return
        
        chain_id = sale_data.get("chain_id", 31337)
        
        async for db in get_db():
            try:
                # Get the current active round for this auction
                round_query = text("""
                    SELECT round_id, kicked_at FROM auction_rounds 
                    WHERE auction_address = :auction_address AND chain_id = :chain_id AND is_active = TRUE
                """)
                
                result = await db.execute(round_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id
                })
                
                round_info = result.fetchone()
                if not round_info:
                    logger.warning(f"No active round found for auction {auction_address}")
                    return
                
                round_id, kicked_at = round_info
                
                # Get next sale sequence for this round
                seq_query = text("""
                    SELECT COALESCE(MAX(sale_seq), 0) + 1 as next_seq 
                    FROM auction_sales 
                    WHERE auction_address = :auction_address AND chain_id = :chain_id AND round_id = :round_id
                """)
                
                seq_result = await db.execute(seq_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "round_id": round_id
                })
                
                next_seq = seq_result.scalar()
                
                # Generate sale ID
                sale_id = f"{auction_address}-{round_id}-{next_seq}"
                
                # Calculate seconds from round start
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                seconds_from_start = int((now - kicked_at).total_seconds())
                
                # Insert sale record
                insert_query = text("""
                    INSERT INTO auction_sales (
                        sale_id, auction_address, chain_id, round_id, sale_seq,
                        taker, from_token, to_token, amount_taken, amount_paid, price,
                        timestamp, seconds_from_round_start,
                        block_number, transaction_hash, log_index
                    )
                    VALUES (
                        :sale_id, :auction_address, :chain_id, :round_id, :sale_seq,
                        :taker, :from_token, :to_token, :amount_taken, :amount_paid, :price,
                        NOW(), :seconds_from_start,
                        :block_number, :transaction_hash, :log_index
                    )
                """)
                
                await db.execute(insert_query, {
                    "sale_id": sale_id,
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "round_id": round_id,
                    "sale_seq": next_seq,
                    "taker": sale_data.get("taker", ""),
                    "from_token": sale_data.get("from_token", ""),
                    "to_token": sale_data.get("to_token", ""),
                    "amount_taken": str(sale_data.get("amount_taken", "0")),
                    "amount_paid": str(sale_data.get("amount_paid", "0")),
                    "price": str(sale_data.get("price", "0")),
                    "seconds_from_start": seconds_from_start,
                    "block_number": sale_data.get("block_number", 0),
                    "transaction_hash": sale_data.get("transaction_hash", ""),
                    "log_index": sale_data.get("log_index", 0)
                })
                
                await db.commit()
                logger.info(f"Recorded sale {sale_id}: {sale_data.get('amount_taken')} tokens")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error recording auction sale: {db_error}")
                raise
            break
            
    except Exception as e:
        logger.error(f"Error recording auction sale: {e}")


async def handle_auction_enabled(event_data: dict):
    """Handle AuctionEnabled events - update auction state"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        from_token = event_data.get("from_token")
        to_token = event_data.get("to_token")
        chain_id = event_data.get("chain_id", 31337)
        
        if is_mock_mode():
            logger.info(f"Mock mode: Would enable auction {auction_address} for {from_token}→{to_token}")
            return
        
        if not auction_address:
            logger.warning("No auction address in AuctionEnabled event")
            return
        
        # Cache token metadata if available
        if from_token:
            await cache_token_metadata(from_token, chain_id)
        if to_token:
            await cache_token_metadata(to_token, chain_id)
            
        logger.info(f"Processed AuctionEnabled: {auction_address} for {from_token}→{to_token}")
    except Exception as e:
        logger.error(f"Error handling AuctionEnabled event: {e}")


async def handle_auction_disabled(event_data: dict):
    """Handle AuctionDisabled events - update auction state"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        from_token = event_data.get("from_token")
        to_token = event_data.get("to_token")
        
        if is_mock_mode():
            logger.info(f"Mock mode: Would disable auction {auction_address} for {from_token}→{to_token}")
            return
        
        if not auction_address:
            logger.warning("No auction address in AuctionDisabled event")
            return
            
        logger.info(f"Processed AuctionDisabled: {auction_address} for {from_token}→{to_token}")
    except Exception as e:
        logger.error(f"Error handling AuctionDisabled event: {e}")


async def handle_updated_starting_price(event_data: dict):
    """Handle UpdatedStartingPrice events - update auction parameters"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        starting_price = event_data.get("starting_price")
        chain_id = event_data.get("chain_id", 31337)
        
        if is_mock_mode():
            logger.info(f"Mock mode: Would update starting price for {auction_address} to {starting_price}")
            return
        
        if not auction_address or not starting_price:
            logger.warning("Missing data in UpdatedStartingPrice event")
            return
        
        async for db in get_db():
            try:
                update_query = text("""
                    UPDATE auction_parameters 
                    SET starting_price = :starting_price
                    WHERE auction_address = :auction_address AND chain_id = :chain_id
                """)
                
                result = await db.execute(update_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "starting_price": str(starting_price)
                })
                
                await db.commit()
                logger.info(f"Updated starting price for {auction_address}: {starting_price}")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error updating starting price: {db_error}")
                raise
            break
            
    except Exception as e:
        logger.error(f"Error handling UpdatedStartingPrice event: {e}")


async def handle_updated_step_decay_rate(event_data: dict):
    """Handle UpdatedStepDecayRate events - update auction parameters"""
    try:
        auction_address = event_data.get("auction_address", event_data.get("auction"))
        step_decay_rate = event_data.get("step_decay_rate")
        chain_id = event_data.get("chain_id", 31337)
        
        if is_mock_mode():
            logger.info(f"Mock mode: Would update step decay rate for {auction_address} to {step_decay_rate}")
            return
        
        if not auction_address or not step_decay_rate:
            logger.warning("Missing data in UpdatedStepDecayRate event")
            return
        
        async for db in get_db():
            try:
                # Convert step_decay_rate from wei to decimal and calculate percentage
                decay_rate_decimal = int(step_decay_rate) / 1e27
                decay_rate_percent = (1 - decay_rate_decimal) * 100
                
                update_query = text("""
                    UPDATE auction_parameters 
                    SET step_decay_rate = :step_decay_rate,
                        decay_rate_percent = :decay_rate_percent
                    WHERE auction_address = :auction_address AND chain_id = :chain_id
                """)
                
                result = await db.execute(update_query, {
                    "auction_address": auction_address,
                    "chain_id": chain_id,
                    "step_decay_rate": str(step_decay_rate),
                    "decay_rate_percent": decay_rate_percent
                })
                
                await db.commit()
                logger.info(f"Updated step decay rate for {auction_address}: {step_decay_rate} ({decay_rate_percent:.4f}%)")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error updating step decay rate: {db_error}")
                raise
            break
            
    except Exception as e:
        logger.error(f"Error handling UpdatedStepDecayRate event: {e}")


async def cache_token_metadata(token_address: str, chain_id: int):
    """Cache basic token metadata"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would cache token metadata for {token_address}")
            return
        
        async for db in get_db():
            try:
                # Check if token already exists
                check_query = text("""
                    SELECT id FROM tokens 
                    WHERE address = :address AND chain_id = :chain_id
                """)
                
                result = await db.execute(check_query, {
                    "address": token_address,
                    "chain_id": chain_id
                })
                
                if result.fetchone():
                    logger.debug(f"Token {token_address} already cached")
                    return
                
                # Insert basic token info (symbol/name/decimals would be fetched from chain)
                insert_query = text("""
                    INSERT INTO tokens (address, chain_id, first_seen)
                    VALUES (:address, :chain_id, NOW())
                    ON CONFLICT (address, chain_id) DO NOTHING
                """)
                
                await db.execute(insert_query, {
                    "address": token_address,
                    "chain_id": chain_id
                })
                
                await db.commit()
                logger.info(f"Cached token metadata for {token_address}")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error caching token metadata: {db_error}")
                raise
            break
            
    except Exception as e:
        logger.error(f"Error caching token metadata: {e}")


async def cache_auction_parameters(auction_address: str, want_token: str, factory_address: str, auction_version: str):
    """Cache immutable auction contract parameters"""
    try:
        if is_mock_mode():
            logger.info(f"Mock mode: Would cache {auction_version} parameters for {auction_address}")
            return
        
        # Set version-specific defaults
        if auction_version == "0.0.1":
            # Legacy auction defaults
            step_decay_rate = int(0.988514020352896135 * 1e27)  # Legacy hardcoded value
            price_update_interval = 60  # Legacy uses 60-second steps
            auction_length = 3600  # 1 hour default for legacy
            decay_rate_percent = ((1 - 0.988514020352896135) * 100)  # ~1.15% per minute
            logger.info(f"Setting legacy defaults for {auction_address}: step_decay_rate={step_decay_rate}, interval=60s")
        else:
            # New auction defaults
            step_decay_rate = int(0.995 * 1e27)  # New default from contract
            price_update_interval = 36  # New STEP_DURATION constant
            auction_length = 3600  # 1 hour default for modern
            decay_rate_percent = ((1 - 0.995) * 100)  # 0.5% per 36 seconds
            logger.info(f"Setting modern defaults for {auction_address}: step_decay_rate={step_decay_rate}, interval=36s")
        
        # Calculate derived fields for UI
        update_interval_minutes = price_update_interval / 60.0
        
        # Insert into database
        async for db in get_db():
            try:
                # Use UPSERT to handle potential duplicates
                query = text("""
                    INSERT INTO auction_parameters (
                        auction_address, chain_id, price_update_interval, step_decay_rate,
                        auction_length, want_token, factory_address, auction_version,
                        decay_rate_percent, update_interval_minutes, discovered_at
                    )
                    VALUES (:auction_address, 31337, :price_update_interval, :step_decay_rate,
                            :auction_length, :want_token, :factory_address, :auction_version,
                            :decay_rate_percent, :update_interval_minutes, NOW())
                    ON CONFLICT (auction_address, chain_id) 
                    DO UPDATE SET
                        step_decay_rate = EXCLUDED.step_decay_rate,
                        price_update_interval = EXCLUDED.price_update_interval,
                        auction_version = EXCLUDED.auction_version,
                        decay_rate_percent = EXCLUDED.decay_rate_percent,
                        update_interval_minutes = EXCLUDED.update_interval_minutes
                """)
                
                await db.execute(query, {
                    "auction_address": auction_address,
                    "price_update_interval": price_update_interval,
                    "step_decay_rate": str(step_decay_rate),
                    "auction_length": auction_length,
                    "want_token": want_token,
                    "factory_address": factory_address,
                    "auction_version": auction_version,
                    "decay_rate_percent": decay_rate_percent,
                    "update_interval_minutes": update_interval_minutes
                })
                
                await db.commit()
                logger.info(f"Cached {auction_version} parameters for auction {auction_address}")
                
            except Exception as db_error:
                await db.rollback()
                logger.error(f"Database error caching auction parameters: {db_error}")
                raise
        
    except Exception as e:
        logger.error(f"Error caching auction parameters: {e}")


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