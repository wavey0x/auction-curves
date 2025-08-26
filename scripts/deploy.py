#!/usr/bin/env python3

from brownie import accounts, Auction, ModifiedAuction, interface
import time

def main():
    # Deploy contracts
    deployer = accounts[0]
    
    print(f"Deploying contracts with account: {deployer}")
    print(f"Account balance: {deployer.balance() / 1e18} ETH")
    
    # Deploy original auction
    print("\nDeploying original Auction contract...")
    original_auction = Auction.deploy({'from': deployer})
    
    # Deploy modified auction  
    print("Deploying ModifiedAuction contract...")
    modified_auction = ModifiedAuction.deploy({'from': deployer})
    
    print(f"\nOriginal Auction deployed at: {original_auction.address}")
    print(f"Modified Auction deployed at: {modified_auction.address}")
    
    return original_auction, modified_auction

if __name__ == "__main__":
    main()