#!/usr/bin/env python3
"""
Continuous activity simulation for testing the auction system.
Simulates various participant behaviors and auction activities.
"""

import asyncio
import json
import random
import time
import os
from datetime import datetime, timezone
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
import logging

# Import brownie components
try:
    from brownie import accounts, Auction, MockERC20Enhanced, network
except ImportError as e:
    print(f"Failed to import brownie contracts: {e}")
    print("Make sure contracts are compiled with: brownie compile")
    print("Run this script with: brownie run scripts/simulate/continuous_activity.py")
    exit(1)

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class ActivitySimulator:
    """Simulates realistic auction activity"""
    
    def __init__(self):
        self.deployment_info = self.load_deployment_info()
        self.accounts = accounts  # Use available accounts for simulation
        self.activity_stats = {
            'kicks_performed': 0,
            'takes_performed': 0,
            'total_volume': 0,
            'participants': set(),
            'start_time': time.time()
        }
        self.participant_profiles = self.create_participant_profiles()
        
    def load_deployment_info(self):
        """Load deployment information"""
        try:
            deployment_path = os.path.join(os.path.dirname(__file__), "../../deployment_info.json")
            if os.path.exists(deployment_path):
                with open(deployment_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded info for {len(data.get('auctions', []))} auctions")
                    return data
        except Exception as e:
            logger.error(f"Could not load deployment info: {e}")
        return {}
    
    def create_participant_profiles(self):
        """Create different types of participants with varying behaviors"""
        profiles = []
        
        # Snipers (wait for specific price points)
        for i in range(3):
            profiles.append({
                'type': 'sniper',
                'account': self.accounts[i],
                'target_discount': random.uniform(0.3, 0.7),  # Wait for 30-70% discount
                'take_size_range': (0.1, 0.3),  # Take 10-30% of available
                'patience': random.uniform(0.8, 0.95),  # Very patient
                'active_probability': 0.3  # Less frequent activity
            })
        
        # Whales (large trades)
        for i in range(3, 6):
            profiles.append({
                'type': 'whale',
                'account': self.accounts[i], 
                'target_discount': random.uniform(0.1, 0.4),  # Earlier entry
                'take_size_range': (0.3, 0.8),  # Large takes
                'patience': random.uniform(0.6, 0.8),
                'active_probability': 0.2  # Selective participation
            })
        
        # Retail traders (frequent small trades)
        for i in range(6, min(10, len(self.accounts))):
            profiles.append({
                'type': 'retail',
                'account': self.accounts[i],
                'target_discount': random.uniform(0.05, 0.25),  # Quick entry
                'take_size_range': (0.05, 0.15),  # Small takes
                'patience': random.uniform(0.3, 0.6),
                'active_probability': 0.8  # Very active
            })
        
        # No arbitrage bots if we only have 10 accounts (6-9 are retail)
        # Arbitrage bots would need additional accounts
        
        return profiles
    
    async def get_kickable_auctions(self):
        """Find auctions that can be kicked"""
        kickable = []
        
        for auction_info in self.deployment_info.get('auctions', []):
            if auction_info.get('kicked', False):
                continue  # Already kicked
            
            try:
                auction = Auction.at(auction_info['address'])
                from_token_address = None
                
                # Find a token to kick (get enabled tokens)
                tokens = self.deployment_info.get('tokens', {})
                for symbol, token_info in tokens.items():
                    if symbol != auction_info['to_token']:  # Not the want token
                        try:
                            # Check if token is enabled and has balance
                            balance = auction.kickable(token_info['address'])
                            if balance > 0:
                                from_token_address = token_info['address']
                                break
                        except:
                            continue
                
                if from_token_address:
                    kickable.append({
                        'auction': auction,
                        'auction_info': auction_info,
                        'from_token': from_token_address
                    })
                    
            except Exception as e:
                logger.debug(f"Error checking kickable status for {auction_info['address']}: {e}")
                continue
        
        return kickable
    
    async def get_active_auctions(self):
        """Get currently active auctions"""
        active = []
        
        for auction_info in self.deployment_info.get('auctions', []):
            if not auction_info.get('kicked', False):
                continue
            
            try:
                auction = Auction.at(auction_info['address'])
                
                # Check enabled auctions
                enabled_auctions = auction.getAllEnabledAuctions()
                
                for token_address in enabled_auctions:
                    if auction.isActive(token_address):
                        available = auction.available(token_address)
                        if available > 0:
                            active.append({
                                'auction': auction,
                                'auction_info': auction_info,
                                'from_token': token_address,
                                'available': available
                            })
                            
            except Exception as e:
                logger.debug(f"Error checking active status for {auction_info['address']}: {e}")
                continue
        
        return active
    
    async def simulate_auction_kick(self):
        """Simulate kicking a random auction"""
        kickable = await self.get_kickable_auctions()
        
        if not kickable:
            return False
        
        # Pick random auction to kick
        auction_data = random.choice(kickable)
        auction = auction_data['auction']
        from_token = auction_data['from_token']
        auction_info = auction_data['auction_info']
        
        try:
            # Pick random account to kick
            kicker = random.choice(self.accounts[:5])  # Use first few accounts as kickers
            
            # Kick the auction
            tx = auction.kick(from_token, {'from': kicker})
            
            # Update deployment info
            auction_info['kicked'] = True
            auction_info['kicked_at'] = tx.timestamp
            
            self.activity_stats['kicks_performed'] += 1
            
            console.print(f"🚀 Kicked auction {auction.address[:10]}... for token {from_token[:10]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error kicking auction: {e}")
            return False
    
    async def simulate_auction_take(self):
        """Simulate taking from an active auction"""
        active_auctions = await self.get_active_auctions()
        
        if not active_auctions:
            return False
        
        # Pick random active auction
        auction_data = random.choice(active_auctions)
        auction = auction_data['auction']
        from_token = auction_data['from_token']
        available = auction_data['available']
        
        # Pick participant based on their behavior profile
        participant = random.choice(self.participant_profiles)
        
        # Check if participant wants to participate
        if random.random() > participant['active_probability']:
            return False
        
        try:
            account = participant['account']
            
            # Calculate current price
            current_price = auction.getAmountNeeded(from_token)
            
            # Get auction parameters for price analysis
            auction_info = auction_data['auction_info']
            starting_price = auction_info.get('starting_price', 1000000)
            
            # Calculate discount from starting price
            if starting_price > 0 and current_price > 0:
                discount = 1 - (current_price / starting_price)
            else:
                discount = 0
            
            # Check if participant wants to take at this price
            if discount < participant['target_discount']:
                return False  # Wait for better price
            
            # Decide take amount based on profile
            min_take, max_take = participant['take_size_range']
            take_percentage = random.uniform(min_take, max_take)
            take_amount = int(available * take_percentage)
            
            if take_amount == 0:
                return False
            
            # Get want token and mint payment tokens
            want_token_symbol = auction_info.get('to_token', 'USDC')
            want_token_info = self.deployment_info.get('tokens', {}).get(want_token_symbol, {})
            
            if want_token_info:
                want_token = MockERC20Enhanced.at(want_token_info['address'])
                
                # Mint enough payment tokens (with buffer)
                payment_needed = current_price * 2  # 2x buffer
                want_token.mint(account.address, payment_needed, {'from': account})
                
                # Approve auction to spend payment tokens
                want_token.approve(auction.address, payment_needed, {'from': account})
            
            # Execute take
            tx = auction.take(from_token, take_amount, {'from': account})
            
            # Update stats
            self.activity_stats['takes_performed'] += 1
            self.activity_stats['participants'].add(str(account))
            self.activity_stats['total_volume'] += current_price
            
            console.print(f"💰 {participant['type'].upper()} took {take_amount} tokens at {discount:.2%} discount")
            return True
            
        except Exception as e:
            logger.debug(f"Error in auction take: {e}")
            return False
    
    def create_activity_table(self) -> Table:
        """Create activity statistics table"""
        table = Table(title="📊 Activity Statistics", title_style="bold green")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Rate", style="yellow")
        
        # Calculate runtime
        runtime = time.time() - self.activity_stats['start_time']
        runtime_hours = runtime / 3600
        
        # Calculate rates
        kicks_per_hour = self.activity_stats['kicks_performed'] / max(runtime_hours, 0.1)
        takes_per_hour = self.activity_stats['takes_performed'] / max(runtime_hours, 0.1)
        
        table.add_row("Auctions Kicked", str(self.activity_stats['kicks_performed']), f"{kicks_per_hour:.1f}/hour")
        table.add_row("Takes Executed", str(self.activity_stats['takes_performed']), f"{takes_per_hour:.1f}/hour")
        table.add_row("Unique Participants", str(len(self.activity_stats['participants'])), "")
        table.add_row("Runtime", f"{runtime/60:.1f} minutes", "")
        
        return table
    
    def create_participant_table(self) -> Table:
        """Create participant behavior table"""
        table = Table(title="👥 Participant Profiles", title_style="bold blue")
        
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Target Discount", style="yellow")
        table.add_column("Take Size", style="magenta")
        
        # Group by type
        type_counts = {}
        type_stats = {}
        
        for profile in self.participant_profiles:
            ptype = profile['type']
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
            
            if ptype not in type_stats:
                type_stats[ptype] = {
                    'discount': [],
                    'take_size': []
                }
            
            type_stats[ptype]['discount'].append(profile['target_discount'])
            take_min, take_max = profile['take_size_range']
            type_stats[ptype]['take_size'].append((take_min + take_max) / 2)
        
        for ptype, count in type_counts.items():
            avg_discount = sum(type_stats[ptype]['discount']) / len(type_stats[ptype]['discount'])
            avg_take_size = sum(type_stats[ptype]['take_size']) / len(type_stats[ptype]['take_size'])
            
            table.add_row(
                ptype.replace('_', ' ').title(),
                str(count),
                f"{avg_discount:.1%}",
                f"{avg_take_size:.1%}"
            )
        
        return table
    
    async def run_continuous_simulation(self):
        """Run continuous activity simulation"""
        console.print(Panel.fit(
            "🎭 [bold green]Starting Continuous Activity Simulation[/bold green]\n"
            "Simulating realistic participant behavior across all auctions...",
            title="Activity Simulator"
        ))
        
        with Live(console=console, refresh_per_second=0.5) as live:
            while True:
                try:
                    # Randomly decide what action to take
                    action = random.choices(
                        ['kick', 'take', 'wait'],
                        weights=[0.1, 0.7, 0.2],  # Mostly takes, some kicks, some waiting
                        k=1
                    )[0]
                    
                    if action == 'kick':
                        await self.simulate_auction_kick()
                    elif action == 'take':
                        await self.simulate_auction_take()
                    # 'wait' does nothing
                    
                    # Update display
                    layout = Panel.fit(
                        f"{self.create_activity_table()}\n\n{self.create_participant_table()}",
                        title="🏛️ Auction Activity Simulation",
                        style="bold green"
                    )
                    
                    live.update(layout)
                    
                    # Random delay between actions (1-30 seconds)
                    delay = random.uniform(1, 30)
                    await asyncio.sleep(delay)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopping activity simulation...[/yellow]")
                    break
                except Exception as e:
                    logger.error(f"Error in simulation loop: {e}")
                    await asyncio.sleep(5)
    
    async def run_burst_activity(self, duration_minutes: int = 10):
        """Run high-frequency activity for testing"""
        console.print(f"🚀 Running {duration_minutes}-minute burst activity simulation...")
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            # High frequency actions
            for _ in range(5):  # 5 actions per cycle
                if random.random() < 0.3:
                    await self.simulate_auction_kick()
                else:
                    await self.simulate_auction_take()
                
                await asyncio.sleep(1)  # 1 second between actions
            
            # Brief pause
            await asyncio.sleep(5)
        
        # Final stats
        console.print(self.create_activity_table())
        console.print(f"✅ Burst activity completed!")

def main():
    """Main function for brownie compatibility"""
    import sys
    
    simulator = ActivitySimulator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--burst":
        # Burst mode for testing
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        asyncio.run(simulator.run_burst_activity(duration))
    else:
        # Continuous simulation mode
        asyncio.run(simulator.run_continuous_simulation())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Simulation stopped by user[/yellow]")