#!/usr/bin/env python3
"""
Pydantic models for Taker data structure.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class TakerSummary(BaseModel):
    """Summary statistics for a taker (used in list views)"""
    taker: str = Field(..., description="Taker wallet address")
    total_takes: int = Field(..., description="Total number of takes")
    unique_auctions: int = Field(..., description="Number of unique auctions participated in")
    unique_chains: int = Field(..., description="Number of unique chains active on")
    total_volume_usd: Optional[str] = Field(None, description="Total USD volume of all takes")
    avg_take_size_usd: Optional[str] = Field(None, description="Average USD value per take")
    first_take: datetime = Field(..., description="Timestamp of first take")
    last_take: datetime = Field(..., description="Timestamp of most recent take")
    active_chains: List[int] = Field(default_factory=list, description="Array of chain IDs where taker is active")
    rank_by_takes: int = Field(..., description="Rank position by total takes count")
    rank_by_volume: int = Field(..., description="Rank position by total USD volume")

class AuctionBreakdown(BaseModel):
    """Taker's activity breakdown by auction"""
    auction_address: str = Field(..., description="Auction contract address")
    chain_id: int = Field(..., description="Chain ID")
    takes_count: int = Field(..., description="Number of takes in this auction")
    volume_usd: Optional[str] = Field(None, description="Total USD volume in this auction")
    last_take: datetime = Field(..., description="Most recent take in this auction")

class TakerDetail(BaseModel):
    """Comprehensive taker information (used in detail views)"""
    taker: str = Field(..., description="Taker wallet address")
    total_takes: int = Field(..., description="Total number of takes")
    unique_auctions: int = Field(..., description="Number of unique auctions participated in")
    unique_chains: int = Field(..., description="Number of unique chains active on")
    total_volume_usd: Optional[str] = Field(None, description="Total USD volume of all takes")
    avg_take_size_usd: Optional[str] = Field(None, description="Average USD value per take")
    first_take: datetime = Field(..., description="Timestamp of first take")
    last_take: datetime = Field(..., description="Timestamp of most recent take")
    active_chains: List[int] = Field(default_factory=list, description="Array of chain IDs where taker is active")
    rank_by_takes: int = Field(..., description="Rank position by total takes count")
    rank_by_volume: int = Field(..., description="Rank position by total USD volume")
    auction_breakdown: List[AuctionBreakdown] = Field(default_factory=list, description="Per-auction activity breakdown")

class TakerListResponse(BaseModel):
    """Paginated taker list response"""
    takers: List[TakerSummary] = Field(..., description="List of takers")
    total: int = Field(..., description="Total number of takers")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")

class TakerTakesResponse(BaseModel):
    """Paginated takes response for a specific taker"""
    takes: List = Field(..., description="List of takes by this taker")  # Using existing Take model from auction.py
    total: int = Field(..., description="Total number of takes by this taker")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")

class TakerFilters(BaseModel):
    """Filters for taker queries"""
    sort_by: str = Field("volume", description="Sort by: volume, takes, or recent")
    chain_id: Optional[int] = Field(None, description="Filter by chain ID")
    page: int = Field(1, ge=1)
    limit: int = Field(25, ge=1, le=100)