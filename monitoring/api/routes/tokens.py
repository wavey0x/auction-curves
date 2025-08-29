#!/usr/bin/env python3
"""
Token-related API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from database import get_db, DatabaseQueries
from models.auction import TokenResponse, TokenInfo

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=TokenResponse)
async def get_tokens(db: AsyncSession = Depends(get_db)):
    """
    Get list of all tokens in the system.
    
    Returns tokens from the token cache and any tokens discovered from auction events.
    """
    try:
        tokens_data = await DatabaseQueries.get_all_tokens(db)
        
        tokens = []
        for token_data in tokens_data:
            token = TokenInfo(
                address=token_data.address,
                symbol=token_data.symbol or "UNKNOWN",
                name=token_data.name or "Unknown Token",
                decimals=token_data.decimals or 18
            )
            tokens.append(token)
        
        return TokenResponse(
            tokens=tokens,
            count=len(tokens)
        )
        
    except Exception as e:
        logger.error(f"Error getting tokens: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{token_address}", response_model=TokenInfo)
async def get_token(
    token_address: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about a specific token.
    
    - **token_address**: The token contract address
    """
    try:
        # Query for specific token
        from sqlalchemy import text
        query = text("""
            SELECT address, symbol, name, decimals
            FROM tokens
            WHERE LOWER(address) = LOWER(:token_address)
            LIMIT 1
        """)
        
        result = await db.execute(query, {"token_address": token_address})
        token_data = result.fetchone()
        
        if not token_data:
            raise HTTPException(status_code=404, detail="Token not found")
        
        return TokenInfo(
            address=token_data.address,
            symbol=token_data.symbol or "UNKNOWN",
            name=token_data.name or "Unknown Token", 
            decimals=token_data.decimals or 18
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token {token_address}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")