#!/usr/bin/env python3
"""
Generate ABI files for Rindexer from Brownie build artifacts.
"""

import json
import os
from pathlib import Path
from brownie import AuctionFactory, Auction

def generate_abis():
    """Generate ABI files from compiled contracts"""
    
    # Create abis directory
    abis_dir = Path(__file__).parent.parent / "indexer" / "rindexer" / "abis"
    abis_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating ABIs in {abis_dir}")
    
    # Generate AuctionFactory ABI
    factory_abi = AuctionFactory.abi
    with open(abis_dir / "AuctionFactory.json", 'w') as f:
        json.dump(factory_abi, f, indent=2)
    print("✅ Generated AuctionFactory.json")
    
    # Generate Auction ABI  
    auction_abi = Auction.abi
    with open(abis_dir / "Auction.json", 'w') as f:
        json.dump(auction_abi, f, indent=2)
    print("✅ Generated Auction.json")
    
    # Generate minimal ERC20 ABI for Transfer events
    erc20_abi = [
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "from", "type": "address"},
                {"indexed": True, "name": "to", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"}
            ],
            "name": "Transfer",
            "type": "event"
        }
    ]
    
    with open(abis_dir / "ERC20.json", 'w') as f:
        json.dump(erc20_abi, f, indent=2)
    print("✅ Generated ERC20.json")
    
    print(f"\n🎉 All ABIs generated successfully!")
    print(f"Files created:")
    for abi_file in abis_dir.glob("*.json"):
        print(f"  - {abi_file}")

def main():
    """Main function"""
    try:
        generate_abis()
    except Exception as e:
        print(f"❌ Error generating ABIs: {e}")
        return False
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)