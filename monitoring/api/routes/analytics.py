#!/usr/bin/env python3
"""
Analytics and system overview endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from ..database import get_db, DatabaseQueries

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/overview")
async def get_system_overview(db: AsyncSession = Depends(get_db)):
    """
    Get system-wide overview and statistics.
    
    Returns high-level metrics about the auction system.
    """
    try:
        # Get basic system stats
        system_stats = await DatabaseQueries.get_system_stats(db)
        
        # Get additional metrics
        from sqlalchemy import text
        
        # Token variety
        token_query = text("SELECT COUNT(DISTINCT address) as token_count FROM tokens")
        token_result = await db.execute(token_query)
        token_count = token_result.scalar() or 0
        
        # Recent activity (last 24 hours)
        activity_query = text("""
            SELECT COUNT(*) as recent_kicks
            FROM auction_kicked 
            WHERE TO_TIMESTAMP(timestamp) >= NOW() - INTERVAL '24 hours'
        """)
        activity_result = await db.execute(activity_query)
        recent_kicks = activity_result.scalar() or 0
        
        return {
            "system_stats": {
                "total_auctions": system_stats.total_auctions if system_stats else 0,
                "active_auctions": system_stats.active_auctions if system_stats else 0,
                "unique_tokens": token_count,
                "total_kicks": system_stats.total_kicks if system_stats else 0
            },
            "activity": {
                "kicks_24h": recent_kicks,
                "avg_kicks_per_hour": round(recent_kicks / 24, 2)
            },
            "health": {
                "database_connected": True,
                "indexing_active": recent_kicks > 0  # Assume indexing is active if recent data
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/token-pairs")
async def get_token_pair_analysis(db: AsyncSession = Depends(get_db)):
    """
    Analyze token pair usage across auctions.
    """
    try:
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                ak.from_token,
                ap.want_token as to_token,
                t1.symbol as from_symbol,
                t2.symbol as to_symbol,
                COUNT(*) as pair_count,
                COUNT(DISTINCT ak.auction) as unique_auctions
            FROM auction_kicked ak
            JOIN auction_parameters ap ON ak.auction = ap.auction_address
            LEFT JOIN tokens t1 ON ak.from_token = t1.address
            LEFT JOIN tokens t2 ON ap.want_token = t2.address  
            GROUP BY ak.from_token, ap.want_token, t1.symbol, t2.symbol
            ORDER BY pair_count DESC
            LIMIT 20
        """)
        
        result = await db.execute(query)
        pairs = result.fetchall()
        
        pair_analysis = []
        for pair in pairs:
            pair_analysis.append({
                "from_token": {
                    "address": pair.from_token,
                    "symbol": pair.from_symbol or "UNKNOWN"
                },
                "to_token": {
                    "address": pair.to_token,
                    "symbol": pair.to_symbol or "UNKNOWN"
                },
                "usage_count": pair.pair_count,
                "unique_auctions": pair.unique_auctions
            })
        
        return {
            "top_pairs": pair_analysis,
            "total_analyzed": len(pair_analysis)
        }
        
    except Exception as e:
        logger.error(f"Error getting token pair analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")