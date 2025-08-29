#!/usr/bin/env python3
"""
Real-time price monitoring service.
Continuously calculates and stores auction prices.
"""

import asyncio
import asyncpg
import json
import time
import os
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from typing import Dict, List, Optional
import logging

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

# Set high precision for calculations
getcontext().prec = 50

# Auction constants
STEP_DURATION = 36  # seconds per step (constant from Auction.sol)
AUCTION_LENGTH = 86400  # 1 day in seconds

# Setup logging and console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class PriceMonitor:
    """Real-time price monitoring for all active auctions"""
    
    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://postgres:password@localhost:5432/auction"
        )
        self.deployment_info = self.load_deployment_info()
        self.price_cache = {}
        self.last_update = time.time()
        
    def load_deployment_info(self):
        """Load deployment information"""
        try:
            deployment_path = os.path.join(os.path.dirname(__file__), "../../deployment_info.json")
            if os.path.exists(deployment_path):
                with open(deployment_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load deployment info: {e}")
        return {}
    
    async def calculate_price(
        self,
        step_duration: int,
        step_decay_rate: str, 
        starting_price: str,
        available_amount: str,
        seconds_elapsed: int
    ) -> Decimal:
        """Calculate auction price using the AuctionHouse formula"""
        try:
            if seconds_elapsed < 0:
                return Decimal('0')
            
            # Convert to high-precision decimals
            step_decay_rate_decimal = Decimal(step_decay_rate) / Decimal('1000000000000000000000000000')
            starting_price_decimal = Decimal(starting_price)
            available_amount_decimal = Decimal(available_amount)
            
            if available_amount_decimal == 0:
                return Decimal('0')
            
            # Calculate steps elapsed using STEP_DURATION
            steps_elapsed = seconds_elapsed // step_duration
            
            # Apply decay: stepDecayRate^stepsElapsed
            decay_factor = step_decay_rate_decimal ** steps_elapsed
            
            # Calculate price: (startingPrice / availableAmount) * decayFactor
            price_per_unit = starting_price_decimal / available_amount_decimal
            current_price = price_per_unit * decay_factor
            
            return current_price
            
        except Exception as e:
            logger.error(f"Price calculation error: {e}")
            return Decimal('0')
    
    async def get_active_auctions(self, conn):
        """Get all currently active auctions"""
        # First try to get data from Rindexer tables if they exist
        check_rindexer_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'auction_round_kicked'
            )
        """
        
        has_rindexer = await conn.fetchval(check_rindexer_query)
        
        if has_rindexer:
            # Use Rindexer event data
            query = """
                SELECT DISTINCT
                    ark.auction as auction_address,
                    ark.from_token,
                    ap.want_token,
                    ark.available as initial_available,
                    TO_TIMESTAMP(ark.timestamp) as kicked_at,
                    COALESCE(ap.step_decay_rate, ap.step_decay) as step_decay_rate,
                    ap.auction_length,
                    ap.starting_price,
                    EXTRACT(EPOCH FROM (NOW() - TO_TIMESTAMP(ark.timestamp))) as seconds_elapsed
                FROM auction_round_kicked ark
                LEFT JOIN auction_parameters ap ON ark.auction = ap.auction_address
                WHERE TO_TIMESTAMP(ark.timestamp) + INTERVAL '1 second' * COALESCE(ap.auction_length, 86400) > NOW()
                ORDER BY ark.timestamp DESC
            """
        else:
            # Use application tables (when no Rindexer data available)
            query = """
                SELECT DISTINCT
                    ar.auction_address,
                    ar.from_token,
                    ap.want_token,
                    ar.initial_available,
                    ar.kicked_at,
                    COALESCE(ap.step_decay_rate, ap.step_decay) as step_decay_rate,
                    ap.auction_length,
                    ap.starting_price,
                    EXTRACT(EPOCH FROM (NOW() - ar.kicked_at)) as seconds_elapsed
                FROM auction_rounds ar
                LEFT JOIN auction_parameters ap ON ar.auction_address = ap.auction_address
                WHERE ar.is_active = TRUE
                ORDER BY ar.kicked_at DESC
            """
        
        rows = await conn.fetch(query)
        return rows
    
    async def store_price_history(self, conn, auction_address: str, price_data: Dict):
        """Store calculated price in price_history table"""
        try:
            await conn.execute("""
                INSERT INTO price_history (
                    auction_address,
                    from_token,
                    timestamp,
                    block_number,
                    price,
                    available_amount,
                    seconds_from_kick
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (auction_address, from_token, timestamp) 
                DO UPDATE SET
                    price = EXCLUDED.price,
                    available_amount = EXCLUDED.available_amount,
                    seconds_from_kick = EXCLUDED.seconds_from_kick
            """,
                auction_address,
                price_data['from_token'],
                datetime.now(timezone.utc),
                0,  # Block number - could be fetched from web3
                str(price_data['price']),
                str(price_data['available']),
                price_data['seconds_from_kick']
            )
        except Exception as e:
            logger.error(f"Error storing price history: {e}")
    
    async def update_all_prices(self):
        """Update prices for all active auctions"""
        conn = await asyncpg.connect(self.db_url)
        try:
            active_auctions = await self.get_active_auctions(conn)
            updated_count = 0
            
            for auction in active_auctions:
                try:
                    # Calculate current price
                    price = await self.calculate_price(
                        STEP_DURATION,  # Use constant step duration
                        str(auction['step_decay_rate'] or "995000000000000000000000000"),
                        str(auction['starting_price'] or "1000000"),
                        str(auction['initial_available'] or "1000000000000000000"),
                        int(auction['seconds_elapsed'])
                    )
                    
                    # Store in cache
                    auction_address = auction['auction_address']
                    self.price_cache[auction_address] = {
                        'price': price,
                        'available': auction['initial_available'],
                        'from_token': auction['from_token'],
                        'want_token': auction['want_token'],
                        'seconds_elapsed': int(auction['seconds_elapsed']),
                        'seconds_from_kick': int(auction['seconds_elapsed']),
                        'time_remaining': max(0, (auction['auction_length'] or 86400) - int(auction['seconds_elapsed'])),
                        'is_active': int(auction['seconds_elapsed']) < (auction['auction_length'] or 86400),
                        'last_updated': time.time()
                    }
                    
                    # Store in database
                    await self.store_price_history(conn, auction_address, self.price_cache[auction_address])
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating auction {auction.get('auction_address', 'unknown')}: {e}")
                    continue
            
            self.last_update = time.time()
            return updated_count
            
        finally:
            await conn.close()
    
    def create_status_table(self) -> Table:
        """Create a status table for live display"""
        table = Table(title="🔍 Auction Price Monitor", title_style="bold cyan")
        
        table.add_column("Auction", style="dim")
        table.add_column("From → To", style="cyan") 
        table.add_column("Current Price", style="green")
        table.add_column("Available", style="yellow")
        table.add_column("Time Left", style="magenta")
        table.add_column("Status", style="bold")
        
        # Sort by last update time
        sorted_auctions = sorted(
            self.price_cache.items(),
            key=lambda x: x[1].get('last_updated', 0),
            reverse=True
        )
        
        for auction_address, data in sorted_auctions[:20]:  # Show top 20
            # Format price
            price = data.get('price', 0)
            if isinstance(price, Decimal):
                if price > 1000000:
                    price_str = f"{price/1000000:.2f}M"
                elif price > 1000:
                    price_str = f"{price/1000:.2f}K" 
                else:
                    price_str = f"{price:.4f}"
            else:
                price_str = "0"
            
            # Format time remaining
            time_remaining = data.get('time_remaining', 0)
            if time_remaining > 3600:
                time_str = f"{time_remaining//3600}h {(time_remaining%3600)//60}m"
            elif time_remaining > 60:
                time_str = f"{time_remaining//60}m {time_remaining%60}s"
            else:
                time_str = f"{time_remaining}s"
            
            # Status
            status = "🟢 ACTIVE" if data.get('is_active', False) else "🔴 ENDED"
            
            table.add_row(
                auction_address[:10] + "...",
                "TOKEN → TOKEN",  # TODO: Get actual symbols
                price_str,
                str(data.get('available', 0))[:10],
                time_str if data.get('is_active', False) else "Ended",
                status
            )
        
        return table
    
    def create_summary_panel(self) -> Panel:
        """Create summary information panel"""
        active_count = sum(1 for data in self.price_cache.values() if data.get('is_active', False))
        total_count = len(self.price_cache)
        
        last_update_str = datetime.fromtimestamp(self.last_update).strftime("%H:%M:%S")
        
        summary_text = f"""
[bold green]Active Auctions:[/bold green] {active_count}
[bold blue]Total Monitored:[/bold blue] {total_count}
[bold yellow]Last Update:[/bold yellow] {last_update_str}
[bold cyan]Update Interval:[/bold cyan] 30 seconds
        """
        
        return Panel(
            summary_text,
            title="📊 Monitor Status",
            title_align="left",
            style="bold"
        )
    
    async def run_continuous_monitoring(self):
        """Run continuous price monitoring with live display"""
        console.print(Panel.fit(
            "🔍 [bold cyan]Starting Auction Price Monitor[/bold cyan]\n"
            "Monitoring all active auctions and calculating real-time prices...",
            title="Price Monitor"
        ))
        
        # Initial update
        await self.update_all_prices()
        
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                try:
                    # Update prices every 30 seconds
                    current_time = time.time()
                    if current_time - self.last_update >= 30:
                        updated_count = await self.update_all_prices()
                        logger.info(f"Updated {updated_count} auction prices")
                    
                    # Update display
                    layout = Panel.fit(
                        f"{self.create_summary_panel()}\n{self.create_status_table()}",
                        title="🏛️ Auction House Price Monitor",
                        style="bold blue"
                    )
                    
                    live.update(layout)
                    await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopping price monitor...[/yellow]")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
    
    async def run_single_update(self):
        """Run a single price update (useful for testing)"""
        console.print("🔍 Running single price update...")
        
        updated_count = await self.update_all_prices()
        
        console.print(f"✅ Updated {updated_count} auctions")
        console.print(self.create_summary_panel())
        console.print(self.create_status_table())

async def main():
    """Main function"""
    import sys
    
    monitor = PriceMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single update mode
        await monitor.run_single_update()
    else:
        # Continuous monitoring mode
        await monitor.run_continuous_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped by user[/yellow]")