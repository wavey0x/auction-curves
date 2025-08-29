#!/usr/bin/env python3
"""
Real-time price calculation service for Dutch auctions.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from decimal import Decimal, getcontext
import logging
import json
import os

from database import get_db, DatabaseQueries

logger = logging.getLogger(__name__)

# Set high precision for decimal calculations
getcontext().prec = 50

# AuctionHouse constants (matching smart contract)
STEP_DURATION = 36  # seconds per step (constant from AuctionHouse.sol)
AUCTION_LENGTH = 86400  # 1 day in seconds (constant from AuctionHouse.sol)

class PriceCalculator:
    """Service for calculating auction prices in real-time"""
    
    def __init__(self):
        self.auction_cache: Dict[str, Dict[str, Any]] = {}
        self.last_update = time.time()
        
    async def initialize(self):
        """Initialize the price calculator with auction data"""
        logger.info("Initializing price calculator...")
        
        try:
            # Load deployment info if available
            deployment_path = os.path.join(os.path.dirname(__file__), "../../../deployment_info.json")
            if os.path.exists(deployment_path):
                with open(deployment_path, 'r') as f:
                    deployment_data = json.load(f)
                    logger.info(f"Loaded deployment info for {len(deployment_data.get('auctions', []))} auctions")
        except Exception as e:
            logger.warning(f"Could not load deployment info: {e}")
        
        logger.info("Price calculator initialized")
    
    async def get_current_price(self, auction_address: str) -> Optional[Decimal]:
        """Calculate the current price for an auction"""
        try:
            async with get_db().__anext__() as db:
                auction_data = await DatabaseQueries.get_auction_details(db, auction_address)
                
                if not auction_data:
                    return None
                
                # Calculate time elapsed since last kick
                if auction_data.last_kicked:
                    kicked_time = auction_data.last_kicked.timestamp()
                    current_time = time.time()
                    seconds_elapsed = current_time - kicked_time
                else:
                    seconds_elapsed = 0
                
                # Check if auction is still active
                auction_length = auction_data.auction_length or AUCTION_LENGTH
                if seconds_elapsed >= auction_length:
                    return Decimal('0')  # Auction ended
                
                return await self.calculate_price_at_time(
                    auction_address,
                    STEP_DURATION,  # Use constant step duration
                    str(auction_data.step_decay_rate or auction_data.step_decay or "995000000000000000000000000"),
                    str(auction_data.starting_price or "1000000"),
                    str(auction_data.current_available or "1000000000000000000"),
                    int(seconds_elapsed)
                )
        
        except Exception as e:
            logger.error(f"Error calculating price for {auction_address}: {e}")
            return None
    
    async def calculate_price_at_time(
        self, 
        auction_address: str,
        step_duration: int,
        step_decay_rate: str,
        starting_price: str,
        available_amount: str,
        seconds_elapsed: int
    ) -> Decimal:
        """
        Calculate auction price at a specific time using the AuctionHouse formula.
        
        This implements the same logic as the AuctionHouse smart contract's _price function.
        Uses STEP_DURATION (36 seconds) and stepDecayRate from the contract.
        """
        try:
            if seconds_elapsed < 0:
                seconds_elapsed = 0
                
            # Convert string values to Decimal for precision
            step_decay_rate_decimal = Decimal(step_decay_rate) / Decimal('1000000000000000000000000000')  # Convert from RAY
            starting_price_decimal = Decimal(starting_price)
            available_amount_decimal = Decimal(available_amount)
            
            if available_amount_decimal == 0:
                return Decimal('0')
            
            # Calculate steps elapsed using STEP_DURATION (36 seconds per step)
            steps_elapsed = seconds_elapsed // step_duration
            
            # Calculate decay factor: stepDecayRate^stepsElapsed
            decay_factor = step_decay_rate_decimal ** steps_elapsed
            
            # Calculate initial price per unit: startingPrice / availableAmount
            initial_price = starting_price_decimal / available_amount_decimal
            
            # Apply decay: initialPrice * decayFactor
            current_price = initial_price * decay_factor
            
            return current_price
            
        except Exception as e:
            logger.error(f"Error in price calculation: {e}")
            return Decimal('0')
    
    async def update_all_prices(self) -> Dict[str, Dict[str, Any]]:
        """Update prices for all active auctions"""
        updated_prices = {}
        
        try:
            async with get_db().__anext__() as db:
                active_auctions = await DatabaseQueries.get_active_auctions(db)
                
                for auction_data in active_auctions:
                    try:
                        auction_address = auction_data.auction_address
                        
                        # Calculate current price
                        current_price = await self.calculate_price_at_time(
                            auction_address,
                            STEP_DURATION,  # Use constant step duration
                            str(auction_data.step_decay_rate or auction_data.step_decay or "995000000000000000000000000"),
                            str(auction_data.starting_price or "1000000"),
                            str(auction_data.initial_available or "1000000000000000000"),
                            int(auction_data.seconds_elapsed)
                        )
                        
                        # Calculate time remaining
                        auction_length = auction_data.auction_length or AUCTION_LENGTH
                        time_remaining = max(0, auction_length - int(auction_data.seconds_elapsed))
                        
                        updated_prices[auction_address] = {
                            "price": str(current_price),
                            "available": str(auction_data.initial_available or 0),
                            "time_remaining": time_remaining,
                            "is_active": time_remaining > 0,
                            "seconds_elapsed": int(auction_data.seconds_elapsed)
                        }
                        
                    except Exception as e:
                        logger.error(f"Error updating price for {auction_data.auction_address}: {e}")
                        continue
                
                self.last_update = time.time()
                
        except Exception as e:
            logger.error(f"Error updating all prices: {e}")
        
        return updated_prices
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()
    
    async def calculate_price_history(
        self, 
        auction_address: str,
        hours: int = 24,
        interval_minutes: int = 5
    ) -> list:
        """
        Calculate theoretical price history for an auction.
        Useful for generating charts when historical data isn't available.
        """
        try:
            async with get_db().__anext__() as db:
                auction_data = await DatabaseQueries.get_auction_details(db, auction_address)
                
                if not auction_data:
                    return []
                
                history_points = []
                total_seconds = hours * 3600
                interval_seconds = interval_minutes * 60
                
                # Generate price points at regular intervals
                for seconds in range(0, total_seconds, interval_seconds):
                    price = await self.calculate_price_at_time(
                        auction_address,
                        STEP_DURATION,  # Use constant step duration
                        str(auction_data.step_decay_rate or auction_data.step_decay or "995000000000000000000000000"),
                        str(auction_data.starting_price or "1000000"),
                        str(auction_data.current_available or "1000000000000000000"),
                        seconds
                    )
                    
                    # Create timestamp relative to auction start
                    base_time = auction_data.last_kicked or datetime.now(timezone.utc)
                    point_time = base_time.timestamp() + seconds
                    
                    history_points.append({
                        "timestamp": datetime.fromtimestamp(point_time, tz=timezone.utc),
                        "price": str(price),
                        "available_amount": str(auction_data.current_available or 0),
                        "seconds_from_kick": seconds
                    })
                
                return history_points
                
        except Exception as e:
            logger.error(f"Error calculating price history for {auction_address}: {e}")
            return []
    
    def format_price_for_display(self, price: Decimal, token_decimals: int = 18) -> str:
        """Format price for human-readable display"""
        try:
            # Convert from wei to human readable format
            human_price = price / (Decimal('10') ** token_decimals)
            
            # Format with appropriate precision
            if human_price >= 1000000:
                return f"{human_price / 1000000:.2f}M"
            elif human_price >= 1000:
                return f"{human_price / 1000:.2f}K"
            elif human_price >= 1:
                return f"{human_price:.4f}"
            else:
                return f"{human_price:.8f}"
                
        except Exception:
            return "0.00"