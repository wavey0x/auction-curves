#!/usr/bin/env python3
"""
Pytest configuration for smart contract tests
"""

import pytest
from brownie import network, accounts, config


def pytest_configure():
    """Configure pytest for brownie testing"""
    # Connect to local network for testing
    if network.is_connected():
        network.disconnect()
    
    # Use development network
    try:
        network.connect('development')
    except:
        # If development network doesn't exist, create it
        network.connect('anvil-local')


@pytest.fixture(scope="session")
def setup_accounts():
    """Setup test accounts"""
    return accounts[:10]  # Use first 10 accounts


@pytest.fixture
def clean_chain():
    """Reset chain state for each test"""
    snapshot = network.chain.snapshot()
    yield
    network.chain.revert(snapshot)