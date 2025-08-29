#!/usr/bin/env python3
"""
Deployment script for AuctionHouseFactory and related contracts.
"""

from brownie import accounts, AuctionFactory, Auction, MockERC20, network
from rich.console import Console
from rich.table import Table

console = Console()

def deploy_factory():
    """Deploy the AuctionFactory contract"""
    console.print("\n🏭 [bold blue]Deploying AuctionFactory...[/bold blue]")
    
    deployer = accounts[0]
    console.print(f"Deploying from account: {deployer}")
    
    # Deploy the factory
    factory = AuctionFactory.deploy({'from': deployer})
    
    console.print(f"✅ AuctionFactory deployed at: [green]{factory.address}[/green]")
    return factory

def deploy_test_tokens():
    """Deploy test tokens for demonstrations"""
    console.print("\n🪙 [bold yellow]Deploying test tokens...[/bold yellow]")
    
    deployer = accounts[0]
    
    # Deploy USDC mock (want token)
    usdc = MockERC20.deploy({'from': deployer})
    console.print(f"✅ Mock USDC deployed at: [green]{usdc.address}[/green]")
    
    # Deploy WETH mock (from token) 
    weth = MockERC20.deploy({'from': deployer})
    console.print(f"✅ Mock WETH deployed at: [green]{weth.address}[/green]")
    
    return usdc, weth

def create_example_auctions(factory, want_token):
    """Create example Auctions with different configurations"""
    console.print("\n🎯 [bold green]Creating example Auctions...[/bold green]")
    
    deployer = accounts[0]
    receiver = accounts[1]
    
    auctions = []
    
    # Standard Auction with default parameters
    tx1 = factory.createNewAuction(
        want_token.address, 
        receiver.address,
        deployer.address,
        1_000_000,  # Default starting price
        {'from': deployer}
    )
    # Get the auction address from events
    auction_address1 = tx1.events['DeployedNewAuction']['auction']
    auctions.append(("Standard", auction_address1))
    
    # Custom Auction with different starting price
    tx2 = factory.createNewAuction(
        want_token.address,
        receiver.address, 
        deployer.address,
        2_000_000,  # 2M starting price
        {'from': deployer}
    )
    auction_address2 = tx2.events['DeployedNewAuction']['auction']
    auctions.append(("Custom", auction_address2))
    
    return auctions

def display_deployment_summary(factory, auctions, want_token, from_tokens):
    """Display a summary of the deployment"""
    console.print("\n📊 [bold cyan]Deployment Summary[/bold cyan]")
    
    # Factory info
    table = Table(title="🏭 AuctionFactory Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Factory Address", factory.address)
    table.add_row("Total Auctions", str(factory.numberOfAuctions()))
    table.add_row("Default Starting Price", f"{factory.DEFAULT_STARTING_PRICE()}")
    # Auction constants are now hardcoded in the contract
    table.add_row("Step Duration", "36 seconds")
    table.add_row("Auction Length", "86400 seconds (1 day)")
    
    console.print(table)
    
    # Auction info
    auction_table = Table(title="🎯 Created Auctions")
    auction_table.add_column("Type", style="cyan")
    auction_table.add_column("Address", style="green")
    auction_table.add_column("Parameters", style="yellow")
    
    for auction_type, auction_address in auctions:
        # Get Auction instance and check parameters
        auction = Auction.at(auction_address)
        starting_price = auction.startingPrice()
        step_decay_rate = auction.stepDecayRate()
        param_str = f"Price: {starting_price}, Decay: {step_decay_rate/1e27:.3f}"
        auction_table.add_row(auction_type, auction_address, param_str)
    
    console.print(auction_table)
    
    # Token info
    token_table = Table(title="🪙 Test Tokens")
    token_table.add_column("Token", style="cyan") 
    token_table.add_column("Address", style="green")
    token_table.add_column("Role", style="yellow")
    
    token_table.add_row("USDC (Mock)", want_token.address, "Want Token (payment)")
    for i, token in enumerate(from_tokens):
        token_table.add_row(f"Token {i+1} (Mock)", token.address, "From Token (Auction asset)")
    
    console.print(token_table)

def main():
    """Main deployment function"""
    console.print("\n🚀 [bold magenta]Auction House Deployment[/bold magenta]")
    console.print(f"Network: [yellow]{network.show_active()}[/yellow]")
    
    try:
        # Deploy factory
        factory = deploy_factory()
        
        # Deploy test tokens
        want_token, from_token = deploy_test_tokens()
        
        # Create example Auctions
        auctions = create_example_auctions(factory, want_token)
        
        # Display summary
        display_deployment_summary(factory, auctions, want_token, [from_token])
        
        console.print("\n✅ [bold green]Deployment completed successfully![/bold green]")
        
        return {
            'factory': factory,
            'want_token': want_token,
            'from_token': from_token,
            'auctions': auctions
        }
        
    except Exception as e:
        console.print(f"\n❌ [bold red]Deployment failed: {str(e)}[/bold red]")
        raise

if __name__ == "__main__":
    main()