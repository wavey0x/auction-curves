#!/usr/bin/env python3
"""
FastAPI backend for Auction House monitoring system.
Serves auction data with real-time WebSocket updates.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import os

from database import get_db, AsyncSession
from models.auction import AuctionResponse, AuctionListResponse, TokenResponse
from routes.auctions import router as auctions_router
from routes.tokens import router as tokens_router
from routes.analytics import router as analytics_router
from services.websocket_manager import WebSocketManager
from services.price_calculator import PriceCalculator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Auction House API",
    description="Real-time auction monitoring and data API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
websocket_manager = WebSocketManager()

# Price calculator
price_calculator = PriceCalculator()

# Include routers
app.include_router(auctions_router, prefix="/api/auctions", tags=["auctions"])
app.include_router(tokens_router, prefix="/api/tokens", tags=["tokens"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

@app.get("/")
async def root():
    """Root endpoint with API status"""
    return {
        "name": "Auction House API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/api/docs",
            "auctions": "/api/auctions",
            "tokens": "/api/tokens",
            "analytics": "/api/analytics",
            "websocket": "/ws"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        result = await db.execute("SELECT 1")
        db_status = "healthy" if result else "unhealthy"
        
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "websocket_connections": len(websocket_manager.active_connections)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@app.websocket("/ws")
async def websocket_global(websocket: WebSocket):
    """Global WebSocket endpoint for all auction updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client messages (subscribe/unsubscribe, etc.)
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.websocket("/ws/auction/{auction_address}")
async def websocket_auction(websocket: WebSocket, auction_address: str):
    """Auction-specific WebSocket endpoint"""
    await websocket_manager.connect(websocket, auction_address)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_websocket_message(websocket, message, auction_address)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, auction_address)

async def handle_websocket_message(websocket: WebSocket, message: Dict[str, Any], auction_address: str = None):
    """Handle incoming WebSocket messages from clients"""
    msg_type = message.get("type")
    
    if msg_type == "subscribe":
        # Client wants to subscribe to specific events
        events = message.get("events", ["price_update", "auction_take", "auction_kick"])
        await websocket.send_text(json.dumps({
            "type": "subscribed",
            "events": events,
            "auction": auction_address
        }))
        
    elif msg_type == "ping":
        # Respond to ping with pong
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))
        
    elif msg_type == "get_current_price":
        # Client requesting current price for auction
        if auction_address:
            try:
                price = await price_calculator.get_current_price(auction_address)
                await websocket.send_text(json.dumps({
                    "type": "current_price",
                    "auction_address": auction_address,
                    "price": str(price) if price else None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": f"Failed to calculate price: {str(e)}"
                }))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Auction House API...")
    
    # Initialize price calculator
    await price_calculator.initialize()
    
    # Start background tasks
    asyncio.create_task(price_update_loop())
    asyncio.create_task(websocket_heartbeat())
    
    logger.info("Auction House API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Auction House API...")
    await websocket_manager.disconnect_all()
    logger.info("Auction House API stopped")

async def price_update_loop():
    """Background task to calculate and broadcast price updates"""
    while True:
        try:
            # Get all active auctions
            db = get_db().__anext__()
            
            # Calculate current prices for active auctions
            updated_prices = await price_calculator.update_all_prices()
            
            # Broadcast updates via WebSocket
            for auction_address, price_data in updated_prices.items():
                await websocket_manager.broadcast_to_auction(auction_address, {
                    "type": "price_update",
                    "auction_address": auction_address,
                    "price": price_data["price"],
                    "available": price_data["available"],
                    "time_remaining": price_data["time_remaining"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            # Also broadcast to global listeners
            await websocket_manager.broadcast_global({
                "type": "price_update_batch", 
                "updates": updated_prices,
                "count": len(updated_prices),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in price update loop: {e}")
        
        # Update every 5 seconds
        await asyncio.sleep(5)

async def websocket_heartbeat():
    """Send periodic heartbeat to keep WebSocket connections alive"""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        
        heartbeat_msg = {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_connections": len(websocket_manager.active_connections)
        }
        
        await websocket_manager.broadcast_global(heartbeat_msg)

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )