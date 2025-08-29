#!/usr/bin/env python3
"""
Quick script to kick auction rounds and generate activity for the UI.
"""

import json
import os
import random
from brownie import accounts, Auction, MockERC20Enhanced, network
from rich.console import Console
from rich.progress import track

console = Console()

def load_deployment_info():
    """Load deployment information"""
    try:
        deployment_path = os.path.join(os.path.dirname(__file__), "../deployment_info.json")
        if os.path.exists(deployment_path):
            with open(deployment_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        console.print(f"[red]Could not load deployment info: {e}[/red]")
    return {}

def kick_auction_rounds():
    """Kick some auction rounds to generate activity"""
    console.print("🚀 [bold green]Starting Quick Auction Round Kicks[/bold green]")
    
    deployment_info = load_deployment_info()
    if not deployment_info:
        console.print("[red]No deployment info found. Run deployment first.[/red]")
        return
    
    auctions = deployment_info.get('auctions', [])
    tokens = deployment_info.get('tokens', {})
    
    if not auctions:
        console.print("[red]No Auctions found in deployment info.[/red]")
        return
    
    console.print(f"Found {len(auctions)} Auctions to kick")
    
    # Kick first 10 Auctions
    kicked_count = 0
    for auction_info in track(auctions[:10], description="Kicking auction rounds..."):
        if auction_info.get('kicked', False):
            continue
            
        try:
            auction = Auction.at(auction_info['address'])
            
            # Find a token to kick
            from_token_address = None
            for symbol, token_info in tokens.items():
                if symbol != auction_info['want_token']:
                    try:
                        balance = auction.kickable(token_info['address'])
                        if balance > 0:
                            from_token_address = token_info['address']
                            break
                    except:
                        continue
            
            if not from_token_address:
                console.print(f"[yellow]No kickable tokens for Auction {auction_info['address'][:10]}...[/yellow]")
                continue
            
            # Pick random account to kick
            kicker = random.choice(accounts[:5])
            
            # Kick the auction round
            tx = auction.kick(from_token_address, {'from': kicker})
            
            # Update deployment info
            auction_info['kicked'] = True
            auction_info['kicked_at'] = tx.timestamp
            auction_info['current_round_id'] = auction.current_round_id(from_token_address)
            
            kicked_count += 1
            console.print(f"✅ Kicked Auction {auction_info['address'][:10]}... for {from_token_address[:10]}...")
            
        except Exception as e:
            console.print(f"[red]Error kicking Auction {auction_info['address'][:10]}...: {e}[/red]")
            continue
    
    # Save updated deployment info
    try:
        deployment_path = os.path.join(os.path.dirname(__file__), "../deployment_info.json")
        with open(deployment_path, 'w') as f:
            json.dump(deployment_info, f, indent=2)
        console.print(f"✅ Updated deployment info with {kicked_count} kicked auction rounds")
    except Exception as e:
        console.print(f"[red]Error saving deployment info: {e}[/red]")

def take_from_auction_rounds():
    """Take from some active auction rounds"""
    console.print("💰 [bold blue]Making Sales from Active Rounds[/bold blue]")
    
    deployment_info = load_deployment_info()
    auctions = deployment_info.get('auctions', [])
    tokens = deployment_info.get('tokens', {})
    
    takes_count = 0
    for auction_info in auctions[:10]:
        if not auction_info.get('kicked', False):
            continue
            
        try:
            auction = Auction.at(auction_info['address'])
            
            # Find active tokens
            enabled_tokens = auction.getAllEnabledTokens()
            
            for token_address in enabled_tokens[:1]:  # Take from first active token
                if auction.isRoundActive(token_address):
                    available = auction.available(token_address)
                    if available > 0:
                        # Pick random account to take
                        taker = random.choice(accounts[5:15])
                        
                        # Take a small amount (10% of available)
                        take_amount = min(available // 10, available)
                        if take_amount == 0:
                            continue
                        
                        # Get want token and mint payment tokens
                        want_token_symbol = auction_info.get('want_token', 'USDC')
                        want_token_info = tokens.get(want_token_symbol, {})
                        
                        if want_token_info:
                            want_token = MockERC20Enhanced.at(want_token_info['address'])
                            
                            # Get current price
                            current_price = auction.getAmountNeeded(token_address, take_amount)
                            payment_needed = current_price * 2  # 2x buffer
                            
                            # Mint payment tokens
                            want_token.mint(taker.address, payment_needed, {'from': taker})
                            want_token.approve(auction.address, payment_needed, {'from': taker})
                            
                            # Execute take (now creates an AuctionSale)
                            tx = auction.take(token_address, take_amount, {'from': taker})
                            
                            takes_count += 1
                            console.print(f"💰 Made sale of {take_amount} tokens from {auction_info['address'][:10]}...")
                        break
                        
        except Exception as e:
            console.print(f"[red]Error making sale from auction round: {e}[/red]")
            continue
    
    console.print(f"✅ Completed {takes_count} sales")

def main():
    """Main function"""
    console.print("[bold cyan]Quick Activity Generator[/bold cyan]")
    console.print("This will kick auctions and generate takes for UI testing\n")
    
    # Connect to network
    if network.is_connected():
        console.print(f"Connected to {network.show_active()}")
    else:
        console.print("[red]Not connected to network[/red]")
        return
    
    # Kick auction rounds first
    kick_auction_rounds()
    
    # Wait a bit then do some sales
    import time
    console.print("\n[yellow]Waiting 5 seconds before making sales...[/yellow]")
    time.sleep(5)
    
    # Make sales from auction rounds
    take_from_auction_rounds()
    
    console.print("\n🎉 [bold green]Activity generation complete![/bold green]")
    console.print("Check the UI at http://localhost:3000 to see the activity")

if __name__ == "__main__":
    main()