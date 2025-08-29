#!/usr/bin/env python3
"""
Data service layer with abstraction for mock vs real data providers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from models.auction import (
    AuctionListItem,
    AuctionResponse,
    AuctionSale,
    AuctionRoundInfo,
    TokenInfo,
    SystemStats
)
from config import get_settings, is_mock_mode, is_development_mode

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Abstract base class for data providers"""
    
    @abstractmethod
    async def get_auctions(
        self, 
        status: str = "all", 
        page: int = 1, 
        limit: int = 20,
        chain_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get paginated list of auctions"""
        pass
    
    @abstractmethod
    async def get_auction_details(self, auction_address: str) -> AuctionResponse:
        """Get detailed auction information"""
        pass
    
    @abstractmethod
    async def get_auction_sales(
        self, 
        auction_address: str, 
        round_id: Optional[int] = None, 
        limit: int = 50
    ) -> List[AuctionSale]:
        """Get sales for an auction"""
        pass
    
    @abstractmethod
    async def get_auction_rounds(
        self, 
        auction_address: str, 
        from_token: str, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get round history for an auction"""
        pass
    
    @abstractmethod
    async def get_tokens(self) -> Dict[str, Any]:
        """Get all tokens"""
        pass
    
    @abstractmethod
    async def get_system_stats(self, chain_id: Optional[int] = None) -> SystemStats:
        """Get system statistics"""
        pass


class MockDataProvider(DataProvider):
    """Mock data provider for testing and development"""
    
    def __init__(self):
        self.mock_tokens = [
            TokenInfo(
                address="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", 
                symbol="USDC", 
                name="USD Coin", 
                decimals=6, 
                chain_id=31337
            ),
            TokenInfo(
                address="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", 
                symbol="USDT", 
                name="Tether USD", 
                decimals=6, 
                chain_id=31337
            ),
            TokenInfo(
                address="0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", 
                symbol="WETH", 
                name="Wrapped Ether", 
                decimals=18, 
                chain_id=31337
            ),
            TokenInfo(
                address="0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9", 
                symbol="WBTC", 
                name="Wrapped Bitcoin", 
                decimals=8, 
                chain_id=31337
            ),
            TokenInfo(
                address="0x5FC8d32690cc91D4c39d9d3abcBD16989F875707", 
                symbol="DAI", 
                name="Dai Stablecoin", 
                decimals=18, 
                chain_id=31337
            ),
        ]
    
    async def get_auctions(
        self, 
        status: str = "all", 
        page: int = 1, 
        limit: int = 20,
        chain_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate mock auction data"""
        auctions = []
        
        for i in range(1, 21):  # 20 mock auctions
            from_tokens = self.mock_tokens[i % 3:(i % 3) + 2] if i % 3 < 3 else self.mock_tokens[:2]
            want_token = self.mock_tokens[(i + 1) % len(self.mock_tokens)]
            
            current_round = None
            if i < 10:  # First 10 are active
                current_round = AuctionRoundInfo(
                    round_id=i % 5 + 1,
                    kicked_at=datetime.now() - timedelta(minutes=i * 30),
                    initial_available=str((i + 1) * 1000 * 10**18),
                    is_active=True,
                    current_price=str(1000000 - (i * 25000)),
                    available_amount=str((20 - i) * 100 * 10**18),
                    time_remaining=3600 - (i * 300),
                    seconds_elapsed=i * 300,
                    total_sales=i % 3 + 1,
                    progress_percentage=(i * 10) % 80
                )
            
            chain_id_to_use = [1, 137, 42161, 10, 56, 31337][i % 6]
            if chain_id and chain_id_to_use != chain_id:
                continue  # Skip if chain filter doesn't match
            
            auction = AuctionListItem(
                address=f"0x{i:040x}",
                chain_id=chain_id_to_use,
                from_tokens=from_tokens,
                want_token=want_token,
                current_round=current_round,
                last_kicked=(datetime.now() - timedelta(hours=i)).isoformat() if i < 15 else None,
                decay_rate_percent=0.5 + (i % 10) * 0.1,
                update_interval_minutes=1.0 + (i % 5) * 0.5
            )
            auctions.append(auction)
        
        # Apply status filter
        if status == "active":
            auctions = [ah for ah in auctions if ah.current_round and ah.current_round.is_active]
        elif status == "completed":
            auctions = [ah for ah in auctions if not ah.current_round or not ah.current_round.is_active]
        
        # Paginate
        total = len(auctions)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated = auctions[start_idx:end_idx]
        
        return {
            "auctions": [auction.dict() for auction in paginated],
            "total": total,
            "page": page,
            "per_page": limit,
            "has_next": end_idx < total
        }
    
    async def get_auction_details(self, auction_address: str) -> AuctionResponse:
        """Generate mock auction details"""
        return AuctionResponse(
            address=auction_address,
            chain_id=31337,
            factory_address="0xfactory123456789",
            deployer="0xdeployer123456",
            from_tokens=[
                TokenInfo(address="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512", symbol="USDC", name="USD Coin", decimals=6, chain_id=31337),
                TokenInfo(address="0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9", symbol="WETH", name="Wrapped Ether", decimals=18, chain_id=31337),
            ],
            want_token=TokenInfo(address="0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0", symbol="USDT", name="Tether USD", decimals=6, chain_id=31337),
            parameters={
                "price_update_interval": 60,
                "step_decay": "995000000000000000000000000",
                "step_decay_rate": "995000000000000000000000000",
                "auction_length": 3600,
                "starting_price": "1000000",
                "fixed_starting_price": None
            },
            current_round=AuctionRoundInfo(
                round_id=3,
                kicked_at=datetime.now() - timedelta(minutes=45),
                initial_available="1000000000000000000000",
                is_active=True,
                current_price="950000",
                available_amount="750000000000000000000",
                time_remaining=2700,
                seconds_elapsed=2700,
                total_sales=5,
                progress_percentage=25.0
            ),
            activity={
                "total_participants": 25,
                "total_volume": "125000000000",
                "total_rounds": 3,
                "total_sales": 15,
                "recent_sales": []
            },
            deployed_at=datetime.now() - timedelta(days=7),
            last_kicked=datetime.now() - timedelta(minutes=45)
        )
    
    async def get_auction_sales(
        self, 
        auction_address: str, 
        round_id: Optional[int] = None, 
        limit: int = 50
    ) -> List[AuctionSale]:
        """Generate mock auction sales"""
        sales = []
        
        for round_num in range(1, 4):
            if round_id and round_num != round_id:
                continue
                
            sales_in_round = 3 + round_num
            for sale_seq in range(1, sales_in_round + 1):
                sale = AuctionSale(
                    sale_id=f"{auction_address}-{round_num}-{sale_seq}",
                    auction=auction_address,
                    chain_id=31337,
                    round_id=round_num,
                    sale_seq=sale_seq,
                    taker=f"0x{(round_num * 10 + sale_seq):040x}",
                    amount_taken=str(sale_seq * 25 * 10**18),
                    amount_paid=str(sale_seq * 22500),
                    price=str(900000 - round_num * 50000 + sale_seq * 1000),
                    timestamp=datetime.now() - timedelta(hours=24 * (4 - round_num), minutes=sale_seq * 15),
                    tx_hash=f"0x{(round_num * 100 + sale_seq):062x}",
                    block_number=1000 + round_num * 10 + sale_seq
                )
                sales.append(sale)
        
        return sales[:limit]
    
    async def get_auction_rounds(
        self, 
        auction_address: str, 
        from_token: str, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """Generate mock auction rounds"""
        rounds = []
        
        for i in range(1, min(limit + 1, 6)):
            is_active = (i == 5)
            round_info = AuctionRoundInfo(
                round_id=i,
                kicked_at=datetime.now() - timedelta(hours=24 * (6 - i)),
                initial_available=str(i * 500 * 10**18),
                is_active=is_active,
                current_price=str(900000 + i * 10000) if is_active else None,
                available_amount=str(i * 100 * 10**18) if is_active else "0",
                time_remaining=1800 if is_active else 0,
                seconds_elapsed=1800 if is_active else 3600,
                total_sales=i * 3,
                progress_percentage=100.0 if not is_active else 50.0
            )
            rounds.append(round_info)
        
        return {
            "auction": auction_address,
            "from_token": from_token,
            "rounds": [round_info.dict() for round_info in rounds],
            "total_rounds": len(rounds)
        }
    
    async def get_tokens(self) -> Dict[str, Any]:
        """Get mock tokens"""
        return {
            "tokens": [token.dict() for token in self.mock_tokens],
            "count": len(self.mock_tokens)
        }
    
    async def get_system_stats(self, chain_id: Optional[int] = None) -> SystemStats:
        """Generate mock system stats"""
        filtered_auctions = 20 if not chain_id else (10 if chain_id == 31337 else 8)
        
        return SystemStats(
            total_auctions=filtered_auctions,
            active_auctions=min(9, filtered_auctions // 2),
            unique_tokens=len([t for t in self.mock_tokens if not chain_id or t.chain_id == chain_id]),
            total_rounds=filtered_auctions * 15,
            total_sales=filtered_auctions * 85,
            total_participants=filtered_auctions * 6
        )


class DatabaseDataProvider(DataProvider):
    """Real database data provider for development/production"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def get_auctions(
        self, 
        status: str = "all", 
        page: int = 1, 
        limit: int = 20,
        chain_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get auctions from database"""
        # TODO: Implement real database queries
        # For now, fallback to mock data
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_auctions(status, page, limit, chain_id)
    
    async def get_auction_details(self, auction_address: str) -> AuctionResponse:
        """Get auction details from database"""
        # TODO: Implement real database queries
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_auction_details(auction_address)
    
    async def get_auction_sales(
        self, 
        auction_address: str, 
        round_id: Optional[int] = None, 
        limit: int = 50
    ) -> List[AuctionSale]:
        """Get auction sales from database"""
        # TODO: Implement real database queries
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_auction_sales(auction_address, round_id, limit)
    
    async def get_auction_rounds(
        self, 
        auction_address: str, 
        from_token: str, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get auction rounds from database"""
        # TODO: Implement real database queries
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_auction_rounds(auction_address, from_token, limit)
    
    async def get_tokens(self) -> Dict[str, Any]:
        """Get tokens from database"""
        # TODO: Implement real database queries
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_tokens()
    
    async def get_system_stats(self, chain_id: Optional[int] = None) -> SystemStats:
        """Get system stats from database"""
        # TODO: Implement real database queries
        logger.warning("DatabaseDataProvider not fully implemented, using mock data")
        mock_provider = MockDataProvider()
        return await mock_provider.get_system_stats(chain_id)


class DataServiceFactory:
    """Factory for creating data service instances"""
    
    @staticmethod
    def create_data_provider(db_session=None) -> DataProvider:
        """Create appropriate data provider based on app mode"""
        settings = get_settings()
        
        if settings.app_mode == "mock":
            logger.info("Using MockDataProvider")
            return MockDataProvider()
        else:
            logger.info("Using DatabaseDataProvider")
            return DatabaseDataProvider(db_session)


# Global data provider instance
_data_provider: Optional[DataProvider] = None


def get_data_provider(db_session=None) -> DataProvider:
    """Get the global data provider instance"""
    global _data_provider
    
    if _data_provider is None:
        _data_provider = DataServiceFactory.create_data_provider(db_session)
    
    return _data_provider


def reset_data_provider():
    """Reset the global data provider (useful for testing)"""
    global _data_provider
    _data_provider = None