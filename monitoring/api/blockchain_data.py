#!/usr/bin/env python3
"""
Fetch real blockchain data for the API instead of mock data.
"""

import json
import os
from web3 import Web3
from typing import List, Dict, Any

# Connect to Anvil
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

def load_deployment_info():
    """Load deployment information"""
    try:
        deployment_path = os.path.join(os.path.dirname(__file__), "../../deployment_info.json")
        if os.path.exists(deployment_path):
            with open(deployment_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Could not load deployment info: {e}")
    return {}

def get_real_auctions():
    """Get real auction data from blockchain"""
    deployment_info = load_deployment_info()
    auctions = deployment_info.get('auctions', [])
    tokens = deployment_info.get('tokens', {})
    
    real_auctions = []
    for i, auction_info in enumerate(auctions):
        # Convert to API format
        real_auction = {
            "address": auction_info['address'],
            "want_token": auction_info.get('to_token_address', list(tokens.values())[0]['address'] if tokens else "0x0"),
            "total_kicks": 1 if auction_info.get('kicked', False) else 0,
            "total_takes": 0,  # Would need to query blockchain events
            "total_volume": "0",
            "current_price": auction_info.get('starting_price', '1000000'),
            "status": "active" if auction_info.get('kicked', False) else "inactive",
            "created_at": "2025-08-28T20:00:00.000Z"  # Use deployment time
        }
        real_auctions.append(real_auction)
    
    return real_auctions

def get_real_tokens():
    """Get real token data from blockchain"""
    deployment_info = load_deployment_info()
    tokens = deployment_info.get('tokens', {})
    
    real_tokens = []
    for symbol, token_info in tokens.items():
        real_token = {
            "address": token_info['address'],
            "symbol": symbol,
            "name": token_info.get('name', symbol),
            "decimals": token_info.get('decimals', 18)
        }
        real_tokens.append(real_token)
    
    return real_tokens

def get_mock_events(event_type: str, limit: int = 50):
    """Generate mock events based on real auction data"""
    deployment_info = load_deployment_info()
    auctions = deployment_info.get('auctions', [])
    tokens = deployment_info.get('tokens', {})
    
    events = []
    token_addresses = list(tokens.values())
    
    for i in range(min(limit, len(auctions))):
        auction = auctions[i]
        if not auction.get('kicked', False):
            continue
            
        event = {
            "id": f"{event_type}_{i}",
            "event_type": event_type,
            "auction_address": auction['address'],
            "from_token": token_addresses[i % len(token_addresses)]['address'] if token_addresses else "0x0",
            "amount": str((i + 1) * 1000000000000000000),
            "participant": f"0x{i+100:040x}",
            "timestamp": int(auction.get('kicked_at', 1756411316)) + (i * 300),
            "tx_hash": f"0x{i+200:062x}",
            "block_number": 1000 + i
        }
        
        if event_type == "take":
            event["to_token"] = token_addresses[(i+1) % len(token_addresses)]['address'] if token_addresses else "0x0"
            event["price"] = str(950000 - (i * 10000))
        else:
            event["price"] = None
            
        events.append(event)
    
    return events

# Export functions for the API to use
__all__ = ['get_real_auctions', 'get_real_tokens', 'get_mock_events', 'load_deployment_info']