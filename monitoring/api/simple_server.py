#!/usr/bin/env python3
"""
Simple standalone API server with new Auction data structure.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta

app = FastAPI(
    title="Auction API",
    description="API for Auction data with round and sale tracking",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data for new structure
mock_tokens = [
    {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6, "chain_id": 31337},
    {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6, "chain_id": 31337},
    {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18, "chain_id": 31337},
    {"address": "0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9", "symbol": "WBTC", "name": "Wrapped Bitcoin", "decimals": 8, "chain_id": 31337},
    {"address": "0x5FC8d32690cc91D4c39d9d3abcBD16989F875707", "symbol": "DAI", "name": "Dai Stablecoin", "decimals": 18, "chain_id": 31337},
]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/auctions")
async def get_auctions(
    status: str = "all",
    page: int = 1,
    limit: int = 20
):
    """Get list of all Auctions"""
    
    auctions = []
    for i in range(1, 21):  # 20 mock Auctions
        from_tokens = mock_tokens[i % 3:(i % 3) + 2] if i % 3 < 3 else mock_tokens[:2]
        want_token = mock_tokens[(i + 1) % len(mock_tokens)]
        
        current_round = None
        if i < 10:  # First 10 are active
            current_round = {
                "round_id": i % 5 + 1,
                "kicked_at": (datetime.now() - timedelta(minutes=i * 30)).isoformat(),
                "initial_available": str((i + 1) * 1000 * 10**18),
                "is_active": True,
                "current_price": str(1000000 - (i * 25000)),
                "available_amount": str((20 - i) * 100 * 10**18),
                "time_remaining": 3600 - (i * 300),
                "seconds_elapsed": i * 300,
                "total_sales": i % 3 + 1,
                "progress_percentage": (i * 10) % 80
            }
        
        auction = {
            "address": f"0x{i:040x}",
            "chain_id": [1, 137, 42161, 10, 56, 31337][i % 6],  # Rotate through different chains
            "from_tokens": from_tokens,
            "want_token": want_token,
            "current_round": current_round,
            "last_kicked": (datetime.now() - timedelta(hours=i)).isoformat(),
            "decay_rate_percent": 0.5 + (i % 10) * 0.1,
            "update_interval_minutes": 1.0 + (i % 5) * 0.5
        }
        auctions.append(auction)
    
    # Apply status filter
    if status == "active":
        auctions = [ah for ah in auctions if ah["current_round"] and ah["current_round"]["is_active"]]
    elif status == "completed":
        auctions = [ah for ah in auctions if not ah["current_round"] or not ah["current_round"]["is_active"]]
    
    # Paginate
    total = len(auctions)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated = auctions[start_idx:end_idx]
    
    return {
        "auctions": paginated,
        "total": total,
        "page": page,
        "per_page": limit,
        "has_next": end_idx < total
    }

@app.get("/auctions/{auction_address}")
async def get_auction_details(auction_address: str):
    """Get detailed Auction information"""
    
    return {
        "address": auction_address,
        "chain_id": 31337,  # Default to Anvil for detailed view
        "factory_address": "0xfactory123456789",
        "deployer": "0xdeployer123456",
        "from_tokens": [
            {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6, "chain_id": 31337},
            {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18, "chain_id": 31337},
        ],
        "want_token": {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6, "chain_id": 31337},
        
        # Fields expected by AuctionDetails UI
        "total_kicks": 12,
        "total_takes": 45,
        "total_volume": "25000000000",  # $25M in wei-like format
        "auction_length": 3600,
        "price_update_interval": 60,
        "starting_price": "1000000000000000000",  # 1 ETH in wei
        "step_decay": "995000000000000000000000000",  # Decay rate
        
        # Enabled tokens for the auction
        "enabled_tokens": [
            {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6, "chain_id": 31337},
            {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18, "chain_id": 31337},
            {"address": "0x5FbDB2315678afecb367f032d93F642f64180aa3", "symbol": "DAI", "name": "Dai Stablecoin", "decimals": 18, "chain_id": 31337},
            {"address": "0x8464135c8F25Da09e49BC8782676a84730C318bC", "symbol": "UNI", "name": "Uniswap Token", "decimals": 18, "chain_id": 31337},
            {"address": "0xa513E6E4b8f2a923D98304ec87F64353C4D5C853", "symbol": "LINK", "name": "ChainLink Token", "decimals": 18, "chain_id": 31337},
        ],
        
        "parameters": {
            "price_update_interval": 60,
            "step_decay": "995000000000000000000000000",  # Deprecated
            "step_decay_rate": "995000000000000000000000000",
            "auction_length": 3600,
            "starting_price": "1000000000000000000",
            "fixed_starting_price": None
        },
        "current_round": {
            "round_id": 3,
            "kicked_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "initial_available": "1000000000000000000000",
            "is_active": True,
            "current_price": "950000",
            "available_amount": "750000000000000000000",
            "time_remaining": 2700,
            "seconds_elapsed": 2700,
            "total_sales": 5,
            "progress_percentage": 25.0
        },
        "activity": {
            "total_participants": 25,
            "total_volume": "125000000000",
            "total_rounds": 3,
            "total_sales": 15,
            "recent_sales": [
                {
                    "sale_id": f"{auction_address}-3-{i+1}",
                    "auction": auction_address,
                    "chain_id": 31337,
                    "round_id": 3,
                    "sale_seq": i + 1,
                    "taker": f"0x{i+100:040x}",
                    "amount_taken": str((i + 1) * 50 * 10**18),
                    "amount_paid": str((i + 1) * 45000),
                    "price": str(900000 + i * 5000),
                    "timestamp": (datetime.now() - timedelta(minutes=40 - i * 8)).isoformat(),
                    "tx_hash": f"0x{i+300:062x}",
                    "block_number": 1000 + i
                } for i in range(5)
            ]
        },
        "deployed_at": (datetime.now() - timedelta(days=7)).isoformat(),
        "last_kicked": (datetime.now() - timedelta(minutes=45)).isoformat(),
    }

@app.get("/auctions/{auction}/rounds")
async def get_auction_rounds(
    auction: str,
    from_token: str,
    limit: int = Query(50, ge=1, le=100)
):
    """Get historical rounds for a specific Auction and token"""
    
    rounds = []
    for i in range(1, min(limit + 1, 6)):  # Up to 5 rounds
        is_active = (i == 5)  # Latest round is active
        round_info = {
            "round_id": i,
            "kicked_at": (datetime.now() - timedelta(hours=24 * (6 - i))).isoformat(),
            "initial_available": str(i * 500 * 10**18),
            "is_active": is_active,
            "current_price": str(900000 + i * 10000) if is_active else None,
            "available_amount": str(i * 100 * 10**18) if is_active else "0",
            "time_remaining": 1800 if is_active else 0,
            "seconds_elapsed": 1800 if is_active else 3600,
            "total_sales": i * 3,
            "progress_percentage": 100.0 if not is_active else 50.0
        }
        rounds.append(round_info)
    
    return {
        "auction": auction,
        "from_token": from_token,
        "rounds": rounds,
        "total_rounds": len(rounds)
    }

@app.get("/auctions/{auction}/sales")
async def get_auction_sales(
    auction: str,
    round_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Get sales/activity for a specific Auction, optionally filtered by round"""
    
    events = []
    
    # Generate kick events (auction start events)
    for round_num in range(1, 13):  # 12 rounds to match total_kicks
        if round_id and round_num != round_id:
            continue
            
        kick_event = {
            "event_id": f"{auction}-kick-{round_num}",
            "event_type": "kick",
            "auction": auction,
            "chain_id": 31337,
            "round_id": round_num,
            "kicker": f"0x{(round_num + 200):040x}",  # Different address for kickers
            "available": str(round_num * 100 * 10**18),  # Amount available for auction
            "starting_price": str(1000000 + round_num * 10000),  # Starting price
            "timestamp": (datetime.now() - timedelta(days=round_num, hours=2)).timestamp(),
            "tx_hash": f"0xkick{round_num:058x}",
            "block_number": 900 + round_num * 5
        }
        events.append(kick_event)
    
    # Generate take events (purchase events)
    for round_num in range(1, 4):  # 3 recent rounds with takes
        if round_id and round_num != round_id:
            continue
            
        sales_in_round = 3 + round_num * 2  # More takes per round
        for sale_seq in range(1, sales_in_round + 1):
            take_event = {
                "event_id": f"{auction}-take-{round_num}-{sale_seq}",
                "event_type": "take",
                "auction": auction,
                "chain_id": 31337,
                "round_id": round_num,
                "sale_seq": sale_seq,
                "taker": f"0x{(round_num * 10 + sale_seq + 50):040x}",
                "amount_taken": str(sale_seq * 25 * 10**18),
                "amount_paid": str(sale_seq * 22500),
                "price": str(900000 - round_num * 50000 + sale_seq * 1000),
                "timestamp": (datetime.now() - timedelta(hours=24 * (4 - round_num), minutes=sale_seq * 15)).timestamp(),
                "tx_hash": f"0xtake{round_num:02x}{sale_seq:056x}",
                "block_number": 1000 + round_num * 10 + sale_seq
            }
            events.append(take_event)
    
    # Sort by timestamp descending (most recent first)
    events.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return events[:limit]

@app.get("/tokens")
async def get_tokens():
    """Get all tokens"""
    return {
        "tokens": mock_tokens,
        "count": len(mock_tokens)
    }

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

@app.get("/chains/{chain_id}")
async def get_chain(chain_id: int):
    """Get specific chain information"""
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
    
    chain = chain_data.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return chain

@app.get("/system/stats")
async def get_system_stats(chain_id: int = None):
    """Get system statistics"""
    # Apply chain filter to mock data
    filtered_auctions = 20 if not chain_id else (10 if chain_id == 31337 else 8)
    
    return {
        "total_auctions": filtered_auctions,
        "active_auctions": min(9, filtered_auctions // 2),
        "unique_tokens": len([t for t in mock_tokens if not chain_id or t["chain_id"] == chain_id]),
        "total_rounds": filtered_auctions * 15,
        "total_sales": filtered_auctions * 85,
        "total_participants": filtered_auctions * 6
    }

@app.get("/analytics/overview")
async def get_system_overview():
    """Get system overview with new metrics - legacy endpoint"""
    stats = await get_system_stats()
    return {
        "system_stats": stats,
        "activity": {
            "rounds_kicked_24h": 12,
            "avg_sales_per_round": 5.0
        },
        "health": {
            "database_connected": True,
            "indexing_active": True
        }
    }

# Legacy endpoints for backwards compatibility during transition
@app.get("/auctions")
async def legacy_get_auctions():
    """Legacy endpoint that maps to auctions"""
    auctions_response = await get_auctions()
    
    # Convert to legacy format
    legacy_auctions = []
    for ah in auctions_response["auctions"]:
        current_round = ah.get("current_round")
        
        auction = {
            "address": ah["address"],
            "want_token": ah["want_token"]["address"],
            "total_kicks": current_round["round_id"] if current_round else 0,
            "total_takes": current_round["total_sales"] if current_round else 0,
            "total_volume": "50000",
            "current_price": current_round["current_price"] if current_round else None,
            "status": 'active' if current_round and current_round["is_active"] else 'inactive',
            "created_at": ah["last_kicked"] if ah["last_kicked"] else datetime.now().isoformat()
        }
        legacy_auctions.append(auction)
    
    return {
        "auctions": legacy_auctions,
        "count": len(legacy_auctions)
    }

@app.get("/activity/kicks")
async def legacy_get_kicks(limit: int = 50):
    """Legacy kicks endpoint - now maps to round kicks"""
    events = []
    
    for i in range(min(limit, 20)):
        event = {
            "id": f"kick_{i}",
            "event_type": "kick",
            "auction_address": f"0x{i:040x}",
            "from_token": mock_tokens[i % len(mock_tokens)]["address"],
            "amount": str((i + 1) * 1000 * 10**18),
            "participant": f"0x{i+100:040x}",
            "timestamp": int(datetime.now().timestamp()) - (i * 300),
            "tx_hash": f"0x{i+200:062x}",
            "block_number": 1000 + i,
            "price": None,
            "round_id": (i % 5) + 1
        }
        events.append(event)
    
    return {
        "events": events,
        "count": len(events),
        "has_more": limit > 20
    }

@app.get("/activity/takes")
async def legacy_get_takes(limit: int = 50):
    """Legacy takes endpoint - now maps to auction sales"""
    events = []
    
    for i in range(min(limit, 20)):
        event = {
            "id": f"take_{i}",
            "event_type": "take",
            "auction_address": f"0x{i:040x}",
            "chain_id": [1, 137, 42161, 10, 56, 31337][i % 6],  # Rotate through chains
            "from_token": mock_tokens[i % len(mock_tokens)]["address"],
            "to_token": mock_tokens[(i+1) % len(mock_tokens)]["address"],
            "amount": str((i + 1) * 500 * 10**18),
            "price": str(950000 - (i * 10000)),
            "participant": f"0x{i+300:040x}",
            "timestamp": int(datetime.now().timestamp()) - (i * 200),
            "tx_hash": f"0x{i+400:062x}",
            "block_number": 1100 + i,
            "round_id": (i % 3) + 1,
            "sale_seq": (i % 5) + 1
        }
        events.append(event)
    
    return {
        "events": events,
        "count": len(events),
        "has_more": limit > 20
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)