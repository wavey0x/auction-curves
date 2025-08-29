#!/usr/bin/env python3
"""
Simple standalone API server for testing the UI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
import os
from datetime import datetime

app = FastAPI(
    title="Auction House API",
    description="Simple API for auction data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import real blockchain data functions
try:
    from blockchain_data import get_real_auctions, get_real_tokens, get_mock_events, load_deployment_info
    USE_REAL_DATA = True
except ImportError:
    USE_REAL_DATA = False
    # Fallback mock data
    mock_tokens = [
        {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6},
        {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6},
        {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18},
        {"address": "0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9", "symbol": "WBTC", "name": "Wrapped Bitcoin", "decimals": 8},
        {"address": "0x5FC8d32690cc91D4c39d9d3abcBD16989F875707", "symbol": "DAI", "name": "Dai Stablecoin", "decimals": 18},
    ]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/auctions")
async def get_auctions():
    """Get list of all auctions"""
    if USE_REAL_DATA:
        try:
            real_auctions = get_real_auctions()
            return {
                "auctions": real_auctions,
                "count": len(real_auctions)
            }
        except Exception as e:
            print(f"Error getting real auctions: {e}")
            # Fall through to mock data
    
    # Fallback mock data
    fallback_tokens = [
        {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6},
        {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6},
        {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18}
    ]
    
    return {
        "auctions": [
            {
                "address": f"0x{i:040x}",
                "want_token": fallback_tokens[i % len(fallback_tokens)]["address"],
                "auction_type": ["linear", "exponential", "conservative"][i % 3],
                "total_kicks": i * 2,
                "total_takes": i * 5,
                "total_volume": str(i * 1000),
                "current_price": str(1000000 - (i * 50000)),
                "status": "active" if i < 10 else "inactive",
                "created_at": datetime.now().isoformat()
            }
            for i in range(1, 21)  # 20 mock auctions
        ],
        "count": 20
    }

@app.get("/auctions/{address}")
async def get_auction(address: str):
    """Get detailed auction information"""
    return {
        "address": address,
        "want_token": mock_tokens[0],
        "auction_length": 86400,
        "starting_price": "1000000",
        "price_update_interval": 60,
        "step_decay": "995000000000000000000000000",  # Deprecated
        "step_decay_rate": "995000000000000000000000000",
        "total_kicks": 5,
        "total_takes": 15,
        "total_volume": "50000",
        "enabled_tokens": mock_tokens[:3],
        "recent_activity": []
    }

@app.get("/activity/kicks")
async def get_kicks(limit: int = 50):
    """Get recent kick events"""
    fallback_tokens = [
        {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6},
        {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6},
        {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18}
    ]
    
    return {
        "events": [
            {
                "id": f"kick_{i}",
                "event_type": "kick",
                "auction_address": f"0x{i:040x}",
                "from_token": fallback_tokens[i % len(fallback_tokens)]["address"],
                "amount": str((i + 1) * 1000000000000000000),
                "participant": f"0x{i+100:040x}",
                "timestamp": int(datetime.now().timestamp()) - (i * 300),
                "tx_hash": f"0x{i+200:062x}",
                "block_number": 1000 + i,
                "price": None
            }
            for i in range(min(limit, 20))
        ],
        "count": min(limit, 20),
        "has_more": limit > 20
    }

@app.get("/activity/takes")
async def get_takes(limit: int = 50):
    """Get recent take events"""
    fallback_tokens = [
        {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6},
        {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6},
        {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18}
    ]
    
    return {
        "events": [
            {
                "id": f"take_{i}",
                "event_type": "take", 
                "auction_address": f"0x{i:040x}",
                "from_token": fallback_tokens[i % len(fallback_tokens)]["address"],
                "to_token": fallback_tokens[(i+1) % len(fallback_tokens)]["address"],
                "amount": str((i + 1) * 500000000000000000),
                "price": str(950000 - (i * 10000)),
                "participant": f"0x{i+300:040x}",
                "timestamp": int(datetime.now().timestamp()) - (i * 200),
                "tx_hash": f"0x{i+400:062x}",
                "block_number": 1100 + i
            }
            for i in range(min(limit, 20))
        ],
        "count": min(limit, 20),
        "has_more": limit > 20
    }

@app.get("/activity/recent")
async def get_recent_activity(limit: int = 50):
    """Get recent activity (kicks and takes combined)"""
    kicks = await get_kicks(limit // 2)
    takes = await get_takes(limit // 2)
    
    all_events = kicks["events"] + takes["events"]
    all_events.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "events": all_events[:limit],
        "count": len(all_events),
        "has_more": False
    }

@app.get("/activity/auction/{address}")
async def get_auction_activity(address: str, limit: int = 50):
    """Get activity for specific auction"""
    return {
        "events": [
            {
                "id": f"event_{i}",
                "event_type": "kick" if i % 3 == 0 else "take",
                "auction_address": address,
                "from_token": mock_tokens[i % len(mock_tokens)]["address"],
                "to_token": mock_tokens[(i+1) % len(mock_tokens)]["address"] if i % 3 != 0 else None,
                "amount": str((i + 1) * 1000000000000000000),
                "price": str(900000 - (i * 5000)) if i % 3 != 0 else None,
                "participant": f"0x{i+500:040x}",
                "timestamp": int(datetime.now().timestamp()) - (i * 600),
                "tx_hash": f"0x{i+600:062x}",
                "block_number": 1200 + i
            }
            for i in range(min(limit, 10))
        ],
        "count": min(limit, 10),
        "has_more": limit > 10
    }

@app.get("/tokens")
async def get_tokens():
    """Get all tokens"""
    if USE_REAL_DATA:
        try:
            real_tokens = get_real_tokens()
            return {
                "tokens": real_tokens,
                "count": len(real_tokens)
            }
        except Exception as e:
            print(f"Error getting real tokens: {e}")
    
    # Fallback mock data
    fallback_tokens = [
        {"address": "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", "symbol": "USDC", "name": "USD Coin", "decimals": 6},
        {"address": "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", "symbol": "USDT", "name": "Tether USD", "decimals": 6},
        {"address": "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", "symbol": "WETH", "name": "Wrapped Ether", "decimals": 18}
    ]
    return {
        "tokens": fallback_tokens,
        "count": len(fallback_tokens)
    }

@app.get("/tokens/{address}")
async def get_token(address: str):
    """Get specific token"""
    # Find token by address
    for token in mock_tokens:
        if token["address"].lower() == address.lower():
            return token
    
    # Default token if not found
    return {
        "address": address,
        "symbol": "UNKNOWN",
        "name": "Unknown Token",
        "decimals": 18
    }

@app.get("/analytics/overview")
async def get_system_overview():
    """Get system overview"""
    return {
        "system_stats": {
            "total_auctions": 100,
            "active_auctions": 15,
            "unique_tokens": len(mock_tokens),
            "total_kicks": 250,
            "total_takes": 1250
        },
        "activity": {
            "kicks_24h": 45,
            "avg_kicks_per_hour": 1.9
        },
        "health": {
            "database_connected": True,
            "indexing_active": True
        }
    }

@app.get("/prices/current")
async def get_current_prices():
    """Get current auction prices"""
    return {
        "prices": [
            {
                "auction_address": f"0x{i:040x}",
                "from_token": mock_tokens[i % len(mock_tokens)]["address"],
                "timestamp": datetime.now().isoformat(),
                "price": str(1000000 - (i * 25000)),
                "available_amount": str((20 - i) * 1000000000000000000),
                "seconds_from_kick": i * 300
            }
            for i in range(1, 16)  # 15 active auctions with prices
        ],
        "count": 15
    }

@app.get("/prices/history/{auction_address}")
async def get_price_history(auction_address: str, from_token: str, hours: int = 24):
    """Get price history for auction"""
    return {
        "prices": [
            {
                "auction_address": auction_address,
                "from_token": from_token,
                "timestamp": datetime.now().isoformat(),
                "price": str(1000000 - (i * 10000)),
                "available_amount": str(1000000000000000000 - (i * 50000000000000000)),
                "seconds_from_kick": i * 600
            }
            for i in range(min(hours, 24))
        ],
        "count": min(hours, 24)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)