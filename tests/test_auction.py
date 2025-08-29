#!/usr/bin/env python3
"""
Unit tests for Auction smart contract
"""

import pytest
from brownie import accounts, Auction, MockERC20Enhanced, reverts
import brownie


class TestAuction:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.owner = accounts[0]
        self.user1 = accounts[1] 
        self.user2 = accounts[2]
        
        # Deploy test tokens
        self.token_a = MockERC20Enhanced.deploy(
            "Test Token A", "TTA", 18, 1000000 * 10**18, 
            {"from": self.owner}
        )
        self.token_b = MockERC20Enhanced.deploy(
            "Test Token B", "TTB", 6, 1000000 * 10**6,
            {"from": self.owner}
        )
        
        # Deploy Auction contract using initialize pattern
        self.auction = Auction.deploy({"from": self.owner})
        
        # Initialize the contract
        self.auction.initialize(
            self.token_b.address,  # want token (what people pay with)
            self.owner,  # receiver of payments
            self.owner,  # governance
            1000000,  # starting price
            {"from": self.owner}
        )
        
        # Give tokens to users
        self.token_a.transfer(self.user1, 100000 * 10**18, {"from": self.owner})
        self.token_b.transfer(self.user1, 100000 * 10**6, {"from": self.owner})
        
    def test_deployment(self):
        """Test Auction deployment and initialization"""
        assert self.auction.governance() == self.owner
        assert self.auction.auctionLength() == 86400  # AUCTION_LENGTH constant
        assert self.auction.startingPrice() == 1000000
        assert self.auction.stepDecayRate() > 0  # Default decay rate
        assert self.auction.want() == self.token_b.address
        
    def test_enable_token(self):
        """Test enabling tokens for Auction"""
        # Only governance can enable tokens
        with reverts():
            self.auction.enable(self.token_a.address, {"from": self.user1})
            
        # Enable token successfully
        tx = self.auction.enable(self.token_a.address, {"from": self.owner})
        
        # Check event emission
        assert 'AuctionEnabled' in tx.events
        assert tx.events['AuctionEnabled']['from'] == self.token_a.address
        assert tx.events['AuctionEnabled']['to'] == self.token_b.address
        
    def test_kick_round(self):
        """Test kicking (starting) an auction round"""
        # Enable token first
        self.auction.enable(self.token_a.address, {"from": self.owner})
        
        # Give Auction contract some tokens
        amount_to_kick = 1000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        # Kick auction round
        tx = self.auction.kick(self.token_a.address, {"from": self.user1})
        
        # Check state changes
        kick_time = tx.timestamp
        kicked_timestamp = self.auction.kicked(self.token_a.address)
        assert kicked_timestamp > 0
        
        # Check event emission
        assert 'AuctionKicked' in tx.events
        event = tx.events['AuctionKicked']
        assert event['from'] == self.token_a.address
        assert event['available'] == amount_to_kick
        
    def test_get_price_calculation(self):
        """Test price calculation over time"""
        # Enable token and kick auction round
        self.auction.enable(self.token_a.address, {"from": self.owner})
        amount_to_kick = 1000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        kick_tx = self.auction.kick(self.token_a.address, {"from": self.user1})
        kick_time = kick_tx.timestamp
        
        # Price should start high and decay over time
        initial_price = self.auction.price(self.token_a.address)
        
        # Wait some time and check price decay (using chain sleep)
        brownie.chain.sleep(36)  # 1 STEP_DURATION
        brownie.chain.mine(1)
        
        price_after_step = self.auction.price(self.token_a.address)
        assert price_after_step < initial_price  # Price should decay
        
        # After more steps
        brownie.chain.sleep(36)  # Another STEP_DURATION
        brownie.chain.mine(1)
        
        price_after_2_steps = self.auction.price(self.token_a.address)
        assert price_after_2_steps < price_after_step
        
    def test_take_from_round(self):
        """Test taking from an active auction round"""
        # Setup Auction (want token already set in initialize)
        self.auction.enable(self.token_a.address, {"from": self.owner})
        
        amount_to_kick = 1000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        # Kick auction round
        kick_tx = self.auction.kick(self.token_a.address, {"from": self.user1})
        
        # Wait some time for price to decay
        brownie.chain.sleep(300)  # 5 minutes
        brownie.chain.mine(1)
        
        # User approves tokens for taking
        take_amount = 100 * 10**6  # 100 USDC equivalent
        self.token_b.approve(self.auction.address, take_amount, {"from": self.user1})
        
        # Take from auction round
        initial_balance_a = self.token_a.balanceOf(self.user1)
        initial_balance_b = self.token_b.balanceOf(self.user1)
        
        # Calculate how much we can get for our payment
        current_price = self.auction.price(self.token_a.address)
        max_take_amount = self.auction.available(self.token_a.address)
        
        tx = self.auction.take(
            self.token_a.address,
            min(max_take_amount, 50 * 10**18),  # Take a reasonable amount
            self.user1,  # receiver
            {"from": self.user1}
        )
        
        # Check balances changed appropriately
        
        # Check token balances changed
        final_balance_a = self.token_a.balanceOf(self.user1)
        final_balance_b = self.token_b.balanceOf(self.user1)
        
        assert final_balance_a > initial_balance_a  # Received token A
        assert final_balance_b < initial_balance_b  # Paid with token B
        
        # The take() function doesn't emit events directly,
        # but should transfer tokens appropriately
        
    def test_price_bounds(self):
        """Test that prices stay within reasonable bounds"""
        # Enable token and kick round
        self.auction.enable(self.token_a.address, {"from": self.owner})
        amount_to_kick = 1000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        kick_tx = self.auction.kick(self.token_a.address, {"from": self.user1})
        kick_time = kick_tx.timestamp
        
        # After auction length, price should be 0
        brownie.chain.sleep(86400 + 1)  # Past AUCTION_LENGTH
        brownie.chain.mine(1)
        
        price_after_end = self.auction.price(self.token_a.address)
        assert price_after_end == 0  # Auction ended
        
    def test_multiple_rounds_same_token(self):
        """Test multiple rounds for the same token"""
        # Enable token
        self.auction.enable(self.token_a.address, {"from": self.owner})
        amount_to_kick = 2000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        # First round
        tx1 = self.auction.kick(self.token_a.address, {"from": self.user1})
        first_kick_time = self.auction.kicked(self.token_a.address)
        assert first_kick_time > 0
        
        # Wait and do second round (after first expires)
        brownie.chain.sleep(86400 + 1)  # Past AUCTION_LENGTH
        brownie.chain.mine(1)
        
        tx2 = self.auction.kick(self.token_a.address, {"from": self.user2})
        second_kick_time = self.auction.kicked(self.token_a.address)
        assert second_kick_time > first_kick_time
        
        assert tx2.timestamp > tx1.timestamp
        
    def test_take_without_active_round_fails(self):
        """Test that taking fails if no round is active"""
        # Enable tokens but don't kick (want token already set in initialize)
        self.auction.enable(self.token_a.address, {"from": self.owner})
        
        # Try to take without active round - should fail
        take_amount = 100 * 10**6
        self.token_b.approve(self.auction.address, take_amount, {"from": self.user1})
        
        with reverts("not kicked"):
            self.auction.take(
                self.token_a.address,
                100 * 10**18,  # amount to take
                self.user1,  # receiver
                {"from": self.user1}
            )
            
    def test_disabled_token_fails(self):
        """Test that operations fail on disabled tokens"""
        # Don't enable token
        amount_to_kick = 1000 * 10**18
        self.token_a.transfer(self.auction.address, amount_to_kick, {"from": self.owner})
        
        # Kick should fail
        with reverts("not enabled"):
            self.auction.kick(self.token_a.address, {"from": self.user1})
            
        # Take should also fail
        with reverts("not kicked"):
            self.auction.take(
                self.token_a.address,
                100 * 10**18,  # amount to take
                self.user1,  # receiver
                {"from": self.user1}
            )