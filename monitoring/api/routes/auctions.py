#!/usr/bin/env python3
"""
FastAPI routes for Auction endpoints with new data structure.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timedelta
from blockchain_data import normalize_address

from models.auction import (
    AuctionResponse,
    AuctionListResponse,
    AuctionListItem,
    AuctionRoundInfo,
    AuctionSale,
    PriceHistoryResponse,
    AuctionRoundHistoryResponse,
    TokenInfo,
    AuctionFilters,
    Take
)

router = APIRouter(prefix="/auctions", tags=["auctions"])

def get_mock_auctions() -> List[AuctionListItem]:
    """Generate mock Auction data with new structure"""
    
    # Mock tokens
    tokens = [
        TokenInfo(address="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", symbol="USDC", name="USD Coin", decimals=6),
        TokenInfo(address="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", symbol="USDT", name="Tether USD", decimals=6),
        TokenInfo(address="0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", symbol="WETH", name="Wrapped Ether", decimals=18),
        TokenInfo(address="0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9", symbol="WBTC", name="Wrapped Bitcoin", decimals=8),
        TokenInfo(address="0x5FC8d32690cc91D4c39d9d3abcBD16989F875707", symbol="DAI", name="Dai Stablecoin", decimals=18),
    ]
    
    auctions = []
    for i in range(1, 21):  # 20 mock Auctions
        # Each Auction has 2-4 enabled tokens
        from_tokens = tokens[i % 3:(i % 3) + 2] if i % 3 < 3 else tokens[:2]
        want_token = tokens[(i + 1) % len(tokens)]
        
        current_round = None
        if i < 10:  # First 10 are active
            current_round = AuctionRoundInfo(
                round_id=i % 5 + 1,  # Round 1-5
                kicked_at=datetime.now() - timedelta(minutes=i * 30),
                initial_available=str((i + 1) * 1000 * 10**18),
                is_active=True,
                current_price=str(1000000 - (i * 25000)),
                available_amount=str((20 - i) * 100 * 10**18),
                time_remaining=3600 - (i * 300),
                seconds_elapsed=i * 300,
                total_takes=i % 3 + 1,
                progress_percentage=(i * 10) % 80
            )
        
        auction = AuctionListItem(
            address=f"0x{i:040x}",
            from_tokens=from_tokens,
            want_token=want_token,
            current_round=current_round,
            last_kicked=datetime.now() - timedelta(hours=i),
            decay_rate=0.995 - (i % 10) * 0.001,
            update_interval=36 + (i % 5) * 6
        )
        auctions.append(auction)
    
    return auctions

@router.get("", response_model=AuctionListResponse)
async def list_auctions(
    filters: AuctionFilters = Depends()
):
    """Get list of all Auctions with optional filters"""
    auctions = get_mock_auctions()
    
    # Apply filters
    if filters.status == "active":
        auctions = [ah for ah in auctions if ah.current_round and ah.current_round.is_active]
    elif filters.status == "completed":
        auctions = [ah for ah in auctions if not ah.current_round or not ah.current_round.is_active]
    
    if filters.from_token:
        auctions = [ah for ah in auctions 
                         if any(token.address.lower() == filters.from_token.lower() for token in ah.from_tokens)]
    
    if filters.want_token:
        auctions = [ah for ah in auctions 
                         if ah.want_token.address.lower() == filters.want_token.lower()]
    
    
    # Sort
    if filters.sort == "kicked_at":
        auctions.sort(key=lambda x: x.last_kicked or datetime.min, 
                           reverse=(filters.order == "desc"))
    elif filters.sort == "address":
        auctions.sort(key=lambda x: x.address, reverse=(filters.order == "desc"))
    
    # Paginate
    total = len(auctions)
    start_idx = (filters.page - 1) * filters.limit
    end_idx = start_idx + filters.limit
    paginated = auctions[start_idx:end_idx]
    
    return AuctionListResponse(
        auctions=paginated,
        total=total,
        page=filters.page,
        per_page=filters.limit,
        has_next=end_idx < total
    )

@router.get("/{auction}", response_model=AuctionResponse)
async def get_auction(auction: str):
    """Get detailed Auction information"""
    # Normalize the auction address to checksummed format
    auction = normalize_address(auction)
    
    from models.auction import AuctionParameters, AuctionActivity
    
    mock_tokens = [
        TokenInfo(address="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", symbol="USDC", name="USD Coin", decimals=6),
        TokenInfo(address="0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", symbol="WETH", name="Wrapped Ether", decimals=18),
    ]
    
    current_round = AuctionRoundInfo(
        round_id=3,
        kicked_at=datetime.now() - timedelta(minutes=45),
        initial_available="1000000000000000000000",
        is_active=True,
        current_price="950000",
        available_amount="750000000000000000000",
        time_remaining=2700,
        seconds_elapsed=2700,
        total_takes=5,
        progress_percentage=25.0
    )
    
    # Mock recent takes
    recent_takes = []
    for i in range(5):
        sale = AuctionSale(
            take_id=f"{auction}-3-{i+1}",
            auction=auction,
            round_id=3,
            take_seq=i + 1,
            taker=f"0x{i+100:040x}",
            amount_taken=str((i + 1) * 50 * 10**18),
            amount_paid=str((i + 1) * 45000),
            price=str(900000 + i * 5000),
            timestamp=datetime.now() - timedelta(minutes=40 - i * 8),
            tx_hash=f"0x{i+300:062x}",
            block_number=1000 + i
        )
        recent_takes.append(sale)
    
    activity = AuctionActivity(
        total_participants=25,
        total_volume="125000000000",
        total_rounds=3,
        total_takes=15,
        recent_takes=recent_takes
    )
    
    return AuctionResponse(
        address=auction,
        factory_address="0xfactory123456789",
        deployer="0xdeployer123456",
        from_tokens=mock_tokens,
        want_token=TokenInfo(address="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", symbol="USDT", name="Tether USD", decimals=6),
        parameters=AuctionParameters(
            price_update_interval=60,
            step_decay="995000000000000000000000000",
            auction_length=3600,
            starting_price="1000000",
            fixed_starting_price=None
        ),
        current_round=current_round,
        activity=activity,
        deployed_at=datetime.now() - timedelta(days=7),
        last_kicked=current_round.kicked_at,
    )

@router.get("/{auction}/rounds", response_model=AuctionRoundHistoryResponse)
async def get_auction_rounds(
    auction: str,
    from_token: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get historical rounds for a specific Auction and token"""
    # Normalize the auction address to checksummed format
    auction = normalize_address(auction)
    
    rounds = []
    for i in range(1, min(limit + 1, 6)):  # Up to 5 rounds
        is_active = (i == 5)  # Latest round is active
        round_info = AuctionRoundInfo(
            round_id=i,
            kicked_at=datetime.now() - timedelta(hours=24 * (6 - i)),
            initial_available=str(i * 500 * 10**18),
            is_active=is_active,
            current_price=str(900000 + i * 10000) if is_active else None,
            available_amount=str(i * 100 * 10**18) if is_active else "0",
            time_remaining=1800 if is_active else 0,
            seconds_elapsed=1800 if is_active else 3600,
            total_takes=i * 3,
            progress_percentage=100.0 if not is_active else 50.0
        )
        rounds.append(round_info)
    
    return AuctionRoundHistoryResponse(
        auction=auction,
        from_token=from_token,
        rounds=rounds,
        total_rounds=len(rounds)
    )

# New takes endpoint
@router.get("/{auction}/takes", response_model=List[Take])
async def get_auction_takes(
    auction: str,
    round_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Get takes for a specific Auction, optionally filtered by round"""
    # Normalize the auction address to checksummed format
    auction = normalize_address(auction)
    
    takes = []
    for round_num in range(1, 4):  # 3 rounds
        if round_id and round_num != round_id:
            continue
            
        takes_in_round = 3 + round_num
        for take_seq in range(1, takes_in_round + 1):
            take = Take(
                take_id=f"{auction}-{round_num}-{take_seq}",
                auction=auction,
                chain_id=31337,
                round_id=round_num,
                take_seq=take_seq,
                taker=f"0x{(round_num * 10 + take_seq):040x}",
                amount_taken=str(take_seq * 25 * 10**18),
                amount_paid=str(take_seq * 22500),
                price=str(900000 - round_num * 50000 + take_seq * 1000),
                timestamp=datetime.now() - timedelta(hours=24 * (4 - round_num), minutes=take_seq * 15),
                tx_hash=f"0x{(round_num * 100 + take_seq):062x}",
                block_number=1000 + round_num * 10 + take_seq
            )
            takes.append(take)
    
    return takes[:limit]


@router.get("/{auction}/price-history", response_model=PriceHistoryResponse)
async def get_price_history(
    auction: str,
    from_token: str,
    hours: int = Query(24, ge=1, le=168)  # Up to 1 week
):
    """Get price history for charting"""
    # Normalize the auction address to checksummed format
    auction = normalize_address(auction)
    
    from models.auction import PriceHistoryPoint
    
    points = []
    current_time = datetime.now()
    
    # Generate price points every 5 minutes for the requested duration
    for i in range(0, hours * 12):  # 12 points per hour (every 5 min)
        timestamp = current_time - timedelta(minutes=i * 5)
        
        # Simulate price decay within rounds
        round_id = (i // 72) + 1  # New round every 6 hours (72 points)
        seconds_from_kick = (i % 72) * 300  # Seconds since round start
        
        # Exponential decay simulation
        starting_price = 1000000
        decay_factor = 0.995 ** (seconds_from_kick // 60)  # Decay every minute
        price = int(starting_price * decay_factor)
        
        available_amount = str(max(0, 1000 * 10**18 - (i % 72) * 10 * 10**18))
        
        point = PriceHistoryPoint(
            timestamp=timestamp,
            price=str(price),
            available_amount=available_amount,
            seconds_from_kick=seconds_from_kick,
            round_id=round_id
        )
        points.append(point)
    
    # Reverse to get chronological order
    points.reverse()
    
    return PriceHistoryResponse(
        auction=auction,
        from_token=from_token,
        points=points,
        duration_hours=hours
    )