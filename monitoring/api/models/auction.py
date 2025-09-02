#!/usr/bin/env python3
"""
Pydantic models for Auction data structure.
"""

from pydantic import BaseModel, Field
try:
    # Pydantic v2
    from pydantic import field_validator as validator
except ImportError:
    # Fallback for pydantic v1
    from pydantic import validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

class TokenInfo(BaseModel):
    """Token information model"""
    address: str = Field(..., description="Token contract address")
    symbol: str = Field(..., description="Token symbol (e.g., WETH)")
    name: str = Field(..., description="Token name (e.g., Wrapped Ether)")
    decimals: int = Field(..., description="Token decimals (6, 8, or 18)")
    chain_id: int = Field(..., description="Chain ID where this token exists")
    
    @validator('address')
    def validate_address(cls, v):
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError('Invalid Ethereum address format')
        return v.lower()

class AuctionParameters(BaseModel):
    """Auction configuration parameters"""
    price_update_interval: int = Field(..., description="Seconds between price updates")
    step_decay: Optional[str] = Field(None, description="DEPRECATED: Decay rate in RAY format (1e27)")
    step_decay_rate: Optional[str] = Field(None, description="Step decay rate per 36-second step (e.g., 0.995 * 1e27)")
    decay_rate: Optional[float] = Field(None, description="Decay rate as decimal (e.g., 0.0115 for 1.15%)")
    auction_length: int = Field(..., description="Total auction round duration in seconds (now AUCTION_LENGTH constant)")
    starting_price: str = Field(..., description="Starting price in wei")
    fixed_starting_price: Optional[str] = Field(None, description="Fixed price if set")
    
    @validator('step_decay', 'step_decay_rate', 'starting_price', 'fixed_starting_price')
    def validate_large_numbers(cls, v):
        if v is not None:
            return str(v)  # Convert to string to handle large numbers
        return v

class AuctionRoundInfo(BaseModel):
    """Information about a specific auction round"""
    round_id: int = Field(..., description="Round ID (1, 2, 3...)")
    kicked_at: datetime = Field(..., description="When this round was kicked")
    round_start: Optional[int] = Field(None, description="Unix timestamp when round started")
    round_end: Optional[int] = Field(None, description="Unix timestamp when round ends")
    initial_available: str = Field(..., description="Initial tokens available for this round")
    is_active: bool = Field(..., description="Whether this round is currently active")
    current_price: Optional[str] = Field(None, description="Current price in wei")
    available_amount: Optional[str] = Field(None, description="Tokens still available")
    time_remaining: Optional[int] = Field(None, description="Seconds until round ends")
    seconds_elapsed: int = Field(..., description="Seconds since round started")
    total_takes: int = Field(0, description="Number of takes in this round")
    progress_percentage: Optional[float] = Field(None, description="Percentage of tokens sold")

class Take(BaseModel):
    """Individual take within an auction round"""
    take_id: str = Field(..., description="Unique take identifier: {auction}-{roundId}-{takeSeq}")
    auction: str = Field(..., description="Auction contract address")
    chain_id: int = Field(..., description="Chain ID where this take occurred")
    round_id: int = Field(..., description="Round ID this take belongs to")
    take_seq: int = Field(..., description="Take sequence number within round (1, 2, 3...)")
    taker: str = Field(..., description="Address that made the purchase")
    amount_taken: str = Field(..., description="Amount of tokens purchased")
    amount_paid: str = Field(..., description="Amount paid in want token")
    price: str = Field(..., description="Price per token at time of take")
    timestamp: datetime = Field(..., description="When the take occurred")
    tx_hash: str = Field(..., description="Transaction hash")
    block_number: int = Field(..., description="Block number")
    # Token information for display
    from_token: Optional[str] = Field(None, description="From token address")
    to_token: Optional[str] = Field(None, description="To token address (want token)")
    from_token_symbol: Optional[str] = Field(None, description="From token symbol")
    from_token_name: Optional[str] = Field(None, description="From token name")
    from_token_decimals: Optional[int] = Field(None, description="From token decimals")
    to_token_symbol: Optional[str] = Field(None, description="To token symbol")
    to_token_name: Optional[str] = Field(None, description="To token name") 
    to_token_decimals: Optional[int] = Field(None, description="To token decimals")
    # USD price information
    from_token_price_usd: Optional[str] = Field(None, description="USD price of from_token at block")
    want_token_price_usd: Optional[str] = Field(None, description="USD price of want_token at block")
    amount_taken_usd: Optional[str] = Field(None, description="USD value of amount taken")
    amount_paid_usd: Optional[str] = Field(None, description="USD value of amount paid")
    price_differential_usd: Optional[str] = Field(None, description="USD differential from auction perspective (positive = auction benefits)")
    price_differential_percent: Optional[float] = Field(None, description="Percentage differential from auction perspective")

class AuctionActivity(BaseModel):
    """Recent activity for an Auction"""
    total_participants: int = Field(0, description="Number of unique participants")
    total_volume: str = Field("0", description="Total volume in want token")
    total_rounds: int = Field(0, description="Total rounds kicked")
    total_takes: int = Field(0, description="Total takes across all rounds")
    recent_takes: List[Take] = Field(default_factory=list, description="Recent takes")

class AuctionResponse(BaseModel):
    """Complete Auction information response"""
    # Basic info
    address: str = Field(..., description="Auction contract address")
    chain_id: int = Field(..., description="Chain ID where this Auction is deployed")
    factory_address: Optional[str] = Field(None, description="Factory that deployed this Auction")
    deployer: str = Field(..., description="Address that deployed the Auction")
    
    # Token information
    from_tokens: List[TokenInfo] = Field(default_factory=list, description="Enabled tokens for sale")
    want_token: TokenInfo = Field(..., description="Token being bought with (want token)")
    
    # Configuration
    parameters: AuctionParameters = Field(..., description="Auction parameters")
    
    # Current round info
    current_round: Optional[AuctionRoundInfo] = Field(None, description="Current active round info per token")
    
    # Activity
    activity: AuctionActivity = Field(default_factory=AuctionActivity, description="Activity metrics")
    
    # Timestamps
    deployed_at: datetime = Field(..., description="When Auction was deployed")
    last_kicked: Optional[datetime] = Field(None, description="When last round started")
    
    # Metadata (auction type concept removed)

class AuctionListItem(BaseModel):
    """Simplified Auction info for list views"""
    address: str
    chain_id: int = Field(..., description="Chain ID where this Auction is deployed")
    from_tokens: List[TokenInfo]
    want_token: TokenInfo
    current_round: Optional[AuctionRoundInfo] = None
    last_kicked: Optional[datetime] = None
    
    # Quick stats
    decay_rate: float = Field(..., description="Decay rate per step (e.g., 0.995)")
    update_interval: int = Field(..., description="Update interval in seconds")

class AuctionListResponse(BaseModel):
    """Paginated Auction list response"""
    auctions: List[AuctionListItem] = Field(..., description="List of Auctions")
    total: int = Field(..., description="Total number of Auctions")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")

class AuctionRoundHistoryResponse(BaseModel):
    """Historical rounds for an Auction"""
    auction: str = Field(..., description="Auction contract address")
    from_token: str = Field(..., description="Token being sold")
    rounds: List[AuctionRoundInfo] = Field(..., description="Historical round data")
    total_rounds: int = Field(..., description="Total number of rounds")

class PriceHistoryPoint(BaseModel):
    """Single point in price history"""
    timestamp: datetime = Field(..., description="Time of price calculation")
    price: str = Field(..., description="Price at this time")
    available_amount: str = Field(..., description="Tokens available at this time")
    seconds_from_kick: int = Field(..., description="Seconds since round started")
    round_id: int = Field(..., description="Which round this price belongs to")

class PriceHistoryResponse(BaseModel):
    """Price history for charting"""
    auction: str = Field(..., description="Auction contract address")
    from_token: str = Field(..., description="Token being sold")
    points: List[PriceHistoryPoint] = Field(..., description="Price history data points")
    duration_hours: int = Field(..., description="Time range in hours")

class TokenResponse(BaseModel):
    """Token information response"""
    tokens: List[TokenInfo] = Field(..., description="List of all tokens")
    count: int = Field(..., description="Total number of tokens")

class AuctionFilters(BaseModel):
    """Filters for Auction queries"""
    status: Optional[str] = Field("all")
    chain_id: Optional[int] = Field(None, description="Filter by chain ID")
    from_token: Optional[str] = Field(None, description="Filter by from token address")
    want_token: Optional[str] = Field(None, description="Filter by want token address")
    sort: str = Field("kicked_at")
    order: str = Field("desc")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

class SystemStats(BaseModel):
    """System statistics"""
    total_auctions: int = Field(..., description="Total number of auctions")
    active_auctions: int = Field(..., description="Number of active auctions")
    unique_tokens: int = Field(..., description="Number of unique tokens")
    total_rounds: int = Field(..., description="Total number of rounds")
    total_takes: int = Field(..., description="Total number of takes")
    total_participants: int = Field(..., description="Total number of participants")
    total_volume_usd: Optional[float] = Field(None, description="Total USD volume of all takes")

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")

class PriceUpdateMessage(WebSocketMessage):
    """Price update WebSocket message"""
    type: str = "price_update"
    auction: str = Field(..., description="Updated Auction address")
    from_token: str = Field(..., description="Token being sold")
    round_id: int = Field(..., description="Round ID")
    price: str = Field(..., description="New price")
    available: str = Field(..., description="Available amount")
    time_remaining: Optional[int] = Field(None, description="Time remaining in seconds")

class AuctionRoundKickMessage(WebSocketMessage):
    """Auction round kick WebSocket message"""
    type: str = "round_kick"
    auction: str = Field(..., description="Auction address")
    from_token: str = Field(..., description="Token being auctioned")
    round_id: int = Field(..., description="New round ID")
    initial_amount: str = Field(..., description="Initial available amount")

class TakeMessage(WebSocketMessage):
    """Auction take WebSocket message"""
    type: str = "take"
    auction: str = Field(..., description="Auction address")
    from_token: str = Field(..., description="Token sold")
    round_id: int = Field(..., description="Round ID")
    take_seq: int = Field(..., description="Take sequence number")
    taker: str = Field(..., description="Address that bought tokens")
    amount_taken: str = Field(..., description="Amount of tokens purchased")
    amount_paid: str = Field(..., description="Amount paid")
    price: str = Field(..., description="Price per token")

# Legacy compatibility models (for backwards compatibility)
class AuctionSummary(BaseModel):
    """Legacy auction summary - maps to AuctionListItem"""
    address: str
    want_token: str
    total_kicks: int  # Maps to total_rounds
    total_takes: int  # Maps to total_takes
    total_volume: str
    current_price: Optional[str] = None
    status: str = 'active'  # 'active' | 'inactive'
    created_at: str

class ActivityEvent(BaseModel):
    """Legacy activity event - maps to AuctionSale or round kick"""
    id: str
    event_type: str  # 'kick' | 'take'  -> 'round_kick' | 'take'
    auction_address: str  # Maps to auction
    chain_id: int = Field(..., description="Chain ID where event occurred")
    from_token: str
    to_token: Optional[str] = None
    amount: str
    price: Optional[str] = None
    participant: str
    timestamp: int
    tx_hash: str
    block_number: int
    
    # New fields for round/sale tracking
    round_id: Optional[int] = None
    take_seq: Optional[int] = None

# Backward compatibility aliases
AuctionSale = Take  # For backward compatibility
AuctionSaleMessage = TakeMessage  # For backward compatibility
