#!/usr/bin/env python3
"""
Taker API routes for analyzing wallet/bot behavior.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from ..database import get_db, DatabaseQueries
from ..models.taker import TakerSummary, TakerDetail, TakerListResponse, TakerTakesResponse

router = APIRouter(prefix="/api/takers", tags=["takers"])

@router.get("", response_model=TakerListResponse)
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
        result = await DatabaseQueries.get_takers_summary(db, sort_by, limit, page, chain_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch takers: {str(e)}"
        )

@router.get("/{taker_address}", response_model=TakerDetail)
async def get_taker_details(
    taker_address: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific taker including rankings and auction breakdown.
    
    - **taker_address**: Ethereum address of the taker wallet
    """
    try:
        result = await DatabaseQueries.get_taker_details(db, taker_address)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch taker details: {str(e)}"
        )

@router.get("/{taker_address}/takes", response_model=TakerTakesResponse)
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
        result = await DatabaseQueries.get_taker_takes(db, taker_address, limit, page)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch taker takes: {str(e)}"
        )