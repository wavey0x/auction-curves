#!/usr/bin/env python3

from brownie import accounts, MinuteStepAuction, MediumStepAuction, SmallStepAuction, interface
import time

def main():
    # Deploy contracts
    deployer = accounts[0]
    
    print(f"Deploying contracts with account: {deployer}")
    print(f"Account balance: {deployer.balance() / 1e18} ETH")
    
    # Deploy all three auction contracts
    print("\nDeploying MinuteStepAuction contract...")
    minute_step_auction = MinuteStepAuction.deploy({'from': deployer})
    
    print("Deploying MediumStepAuction contract...")
    medium_step_auction = MediumStepAuction.deploy({'from': deployer})
    
    print("Deploying SmallStepAuction contract...")
    small_step_auction = SmallStepAuction.deploy({'from': deployer})
    
    print(f"\nMinute-Step Auction deployed at: {minute_step_auction.address}")
    print(f"Medium-Step Auction deployed at: {medium_step_auction.address}")
    print(f"Small-Step Auction deployed at: {small_step_auction.address}")
    
    return minute_step_auction, medium_step_auction, small_step_auction

if __name__ == "__main__":
    main()