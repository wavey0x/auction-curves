#!/usr/bin/env python3
"""
WebSocket connection manager for real-time auction updates.
"""

import json
import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Global connections (receive all updates)
        self.active_connections: List[WebSocket] = []
        
        # Auction-specific connections
        self.auction_connections: Dict[str, List[WebSocket]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, auction_address: Optional[str] = None):
        """Connect a WebSocket client"""
        await websocket.accept()
        
        if auction_address:
            # Auction-specific connection
            if auction_address not in self.auction_connections:
                self.auction_connections[auction_address] = []
            self.auction_connections[auction_address].append(websocket)
            
            self.connection_metadata[websocket] = {
                "type": "auction_specific",
                "auction_address": auction_address,
                "connected_at": datetime.now(timezone.utc),
                "message_count": 0
            }
            
            logger.info(f"WebSocket connected to auction {auction_address}")
            
            # Send welcome message with auction info
            await self._send_to_websocket(websocket, {
                "type": "connection_established",
                "auction_address": auction_address,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        else:
            # Global connection
            self.active_connections.append(websocket)
            
            self.connection_metadata[websocket] = {
                "type": "global",
                "connected_at": datetime.now(timezone.utc),
                "message_count": 0
            }
            
            logger.info("Global WebSocket connected")
            
            # Send welcome message
            await self._send_to_websocket(websocket, {
                "type": "connection_established",
                "connection_type": "global",
                "active_auctions": len(self.auction_connections),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    def disconnect(self, websocket: WebSocket, auction_address: Optional[str] = None):
        """Disconnect a WebSocket client"""
        try:
            if auction_address and auction_address in self.auction_connections:
                if websocket in self.auction_connections[auction_address]:
                    self.auction_connections[auction_address].remove(websocket)
                    
                    # Clean up empty auction lists
                    if not self.auction_connections[auction_address]:
                        del self.auction_connections[auction_address]
                    
                    logger.info(f"WebSocket disconnected from auction {auction_address}")
            
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info("Global WebSocket disconnected")
            
            # Clean up metadata
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
                
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def disconnect_all(self):
        """Disconnect all WebSocket clients"""
        # Close global connections
        for websocket in self.active_connections.copy():
            try:
                await websocket.close()
            except:
                pass
        self.active_connections.clear()
        
        # Close auction-specific connections
        for auction_address, connections in self.auction_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.close()
                except:
                    pass
        self.auction_connections.clear()
        
        # Clear metadata
        self.connection_metadata.clear()
        
        logger.info("All WebSocket connections closed")
    
    async def broadcast_global(self, message: Dict[str, Any]):
        """Broadcast message to all global connections"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        
        # Send to all global connections
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_json)
                
                # Update message count
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending to global WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)
        
        if len(self.active_connections) > 0:
            logger.debug(f"Broadcasted to {len(self.active_connections)} global connections")
    
    async def broadcast_to_auction(self, auction_address: str, message: Dict[str, Any]):
        """Broadcast message to connections watching a specific auction"""
        if auction_address not in self.auction_connections:
            return
        
        connections = self.auction_connections[auction_address]
        if not connections:
            return
        
        message_json = json.dumps(message, default=str)
        
        # Send to auction-specific connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message_json)
                
                # Update message count
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending to auction WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket, auction_address)
        
        if len(connections) > 0:
            logger.debug(f"Broadcasted to {len(connections)} connections for auction {auction_address}")
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific connection"""
        try:
            await self._send_to_websocket(websocket, message)
        except Exception as e:
            logger.error(f"Error sending to specific WebSocket: {e}")
            # Find and disconnect the failed connection
            if websocket in self.active_connections:
                self.disconnect(websocket)
            else:
                # Find in auction connections
                for auction_address, connections in self.auction_connections.items():
                    if websocket in connections:
                        self.disconnect(websocket, auction_address)
                        break
    
    async def _send_to_websocket(self, websocket: WebSocket, message: Dict[str, Any]):
        """Internal method to send message to websocket with error handling"""
        message_json = json.dumps(message, default=str)
        await websocket.send_text(message_json)
        
        # Update message count
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["message_count"] += 1
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections"""
        auction_stats = {}
        for auction_address, connections in self.auction_connections.items():
            auction_stats[auction_address] = len(connections)
        
        total_messages = sum(
            metadata.get("message_count", 0) 
            for metadata in self.connection_metadata.values()
        )
        
        return {
            "global_connections": len(self.active_connections),
            "auction_connections": auction_stats,
            "total_auction_connections": sum(len(conns) for conns in self.auction_connections.values()),
            "total_connections": len(self.connection_metadata),
            "total_messages_sent": total_messages,
            "tracked_auctions": list(self.auction_connections.keys())
        }
    
    async def send_heartbeat(self):
        """Send heartbeat to all connections"""
        heartbeat_msg = {
            "type": "heartbeat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": self.get_connection_stats()
        }
        
        # Send to global connections
        await self.broadcast_global(heartbeat_msg)
        
        # Send to auction-specific connections
        for auction_address in self.auction_connections:
            await self.broadcast_to_auction(auction_address, {
                **heartbeat_msg,
                "auction_address": auction_address
            })
    
    async def notify_price_update(self, auction_address: str, price_data: Dict[str, Any]):
        """Notify about price updates for an auction"""
        message = {
            "type": "price_update",
            "auction_address": auction_address,
            "price": price_data.get("price"),
            "available": price_data.get("available"),
            "time_remaining": price_data.get("time_remaining"),
            "is_active": price_data.get("is_active"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to auction-specific connections
        await self.broadcast_to_auction(auction_address, message)
        
        # Also send to global connections
        await self.broadcast_global(message)
    
    async def notify_auction_kick(self, auction_address: str, kick_data: Dict[str, Any]):
        """Notify about new auction kicks"""
        message = {
            "type": "auction_kick",
            "auction_address": auction_address,
            "from_token": kick_data.get("from_token"),
            "initial_amount": kick_data.get("initial_amount"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_auction(auction_address, message)
        await self.broadcast_global(message)
    
    async def notify_auction_take(self, auction_address: str, take_data: Dict[str, Any]):
        """Notify about auction takes"""
        message = {
            "type": "auction_take", 
            "auction_address": auction_address,
            "taker": take_data.get("taker"),
            "amount_taken": take_data.get("amount_taken"),
            "amount_paid": take_data.get("amount_paid"),
            "price": take_data.get("price"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.broadcast_to_auction(auction_address, message)
        await self.broadcast_global(message)