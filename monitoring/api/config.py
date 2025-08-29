#!/usr/bin/env python3
"""
Configuration management for Auction API.
Supports mock, development, and production modes.
"""

import os
from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class AppMode(str, Enum):
    """Application running modes"""
    MOCK = "mock"
    DEV = "dev"
    DEVELOPMENT = "development" 
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings with environment-based configuration"""
    
    # Application mode
    app_mode: AppMode = AppMode.MOCK
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    # Database settings (only used in development/production)
    database_url: Optional[str] = None
    
    # Blockchain settings (legacy - for backwards compatibility)
    anvil_rpc_url: str = "http://localhost:8545"
    web3_infura_project_id: Optional[str] = None
    
    # Rindexer settings (only used in development/production)
    rindexer_database_url: Optional[str] = None
    rindexer_rpc_url: str = "http://localhost:8545"
    
    # Factory contract settings (legacy - for backwards compatibility)
    factory_address: Optional[str] = None
    start_block: int = 0
    
    # Multi-Network Configuration
    networks_enabled: str = "local"  # Comma-separated list: "ethereum,polygon,arbitrum"
    
    # Network-specific RPC URLs
    ethereum_rpc_url: Optional[str] = None
    polygon_rpc_url: Optional[str] = None
    arbitrum_rpc_url: Optional[str] = None
    optimism_rpc_url: Optional[str] = None
    base_rpc_url: Optional[str] = None
    
    # Network-specific factory addresses
    ethereum_factory_address: Optional[str] = None
    polygon_factory_address: Optional[str] = None
    arbitrum_factory_address: Optional[str] = None
    optimism_factory_address: Optional[str] = None
    base_factory_address: Optional[str] = None
    local_factory_address: Optional[str] = None
    
    # Network-specific start blocks
    ethereum_start_block: Optional[int] = 18000000
    polygon_start_block: Optional[int] = 45000000
    arbitrum_start_block: Optional[int] = 100000000
    optimism_start_block: Optional[int] = 100000000
    base_start_block: Optional[int] = 1000000
    local_start_block: Optional[int] = 0
    
    @field_validator('ethereum_start_block', 'polygon_start_block', 'arbitrum_start_block', 
                     'optimism_start_block', 'base_start_block', 'local_start_block', mode='before')
    @classmethod
    def parse_start_block(cls, v):
        """Handle empty strings for start block fields"""
        if v == '' or v is None:
            return None
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return None
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Override env file based on APP_MODE
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            app_mode = os.getenv("APP_MODE", "mock")
            
            # Try to load mode-specific env file
            mode_env_file = f".env.{app_mode}"
            if os.path.exists(mode_env_file):
                env_settings.env_file = mode_env_file
            
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def is_mock_mode() -> bool:
    """Check if running in mock mode"""
    return settings.app_mode == AppMode.MOCK


def is_development_mode() -> bool:
    """Check if running in development mode"""
    return settings.app_mode in [AppMode.DEVELOPMENT, AppMode.DEV]


def is_production_mode() -> bool:
    """Check if running in production mode"""
    return settings.app_mode == AppMode.PRODUCTION


def requires_database() -> bool:
    """Check if current mode requires database connection"""
    return settings.app_mode in [AppMode.DEVELOPMENT, AppMode.DEV, AppMode.PRODUCTION]


def get_cors_origins() -> list:
    """Get CORS origins as a list"""
    return [origin.strip() for origin in settings.cors_origins.split(",")]


# Network definitions with metadata
SUPPORTED_NETWORKS = {
    "ethereum": {
        "chain_id": 1,
        "name": "Ethereum Mainnet",
        "short_name": "Ethereum",
        "rpc_key": "ethereum_rpc_url",
        "factory_key": "ethereum_factory_address",
        "start_block_key": "ethereum_start_block",
        "explorer": "https://etherscan.io",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_ethereum.jpg"
    },
    "polygon": {
        "chain_id": 137,
        "name": "Polygon",
        "short_name": "Polygon",
        "rpc_key": "polygon_rpc_url",
        "factory_key": "polygon_factory_address",
        "start_block_key": "polygon_start_block",
        "explorer": "https://polygonscan.com",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_polygon.jpg"
    },
    "arbitrum": {
        "chain_id": 42161,
        "name": "Arbitrum One",
        "short_name": "Arbitrum",
        "rpc_key": "arbitrum_rpc_url",
        "factory_key": "arbitrum_factory_address",
        "start_block_key": "arbitrum_start_block",
        "explorer": "https://arbiscan.io",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_arbitrum.jpg"
    },
    "optimism": {
        "chain_id": 10,
        "name": "Optimism",
        "short_name": "Optimism",
        "rpc_key": "optimism_rpc_url",
        "factory_key": "optimism_factory_address",
        "start_block_key": "optimism_start_block",
        "explorer": "https://optimistic.etherscan.io",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_optimism.jpg"
    },
    "base": {
        "chain_id": 8453,
        "name": "Base",
        "short_name": "Base",
        "rpc_key": "base_rpc_url",
        "factory_key": "base_factory_address",
        "start_block_key": "base_start_block",
        "explorer": "https://basescan.org",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_base.jpg"
    },
    "local": {
        "chain_id": 31337,
        "name": "Anvil Local",
        "short_name": "Anvil",
        "rpc_key": "anvil_rpc_url",  # Uses legacy key for backwards compatibility
        "factory_key": "local_factory_address",
        "start_block_key": "local_start_block",
        "explorer": "#",
        "icon": "https://icons.llamao.fi/icons/chains/rsz_ethereum.jpg"
    }
}


def get_enabled_networks() -> list:
    """Get list of enabled network names"""
    return [name.strip() for name in settings.networks_enabled.split(",")]


def get_network_config(network_name: str) -> dict:
    """Get configuration for a specific network"""
    if network_name not in SUPPORTED_NETWORKS:
        raise ValueError(f"Unsupported network: {network_name}")
    
    network_meta = SUPPORTED_NETWORKS[network_name]
    config = network_meta.copy()
    
    # Add actual values from settings
    config["rpc_url"] = getattr(settings, network_meta["rpc_key"], None)
    config["factory_address"] = getattr(settings, network_meta["factory_key"], None)
    start_block_value = getattr(settings, network_meta["start_block_key"], 0)
    config["start_block"] = start_block_value if start_block_value is not None else 0
    
    return config


def get_all_network_configs() -> dict:
    """Get configurations for all enabled networks"""
    enabled = get_enabled_networks()
    return {
        name: get_network_config(name) 
        for name in enabled 
        if name in SUPPORTED_NETWORKS
    }


def validate_settings():
    """Validate settings based on app mode"""
    if requires_database():
        if not settings.database_url:
            raise ValueError(f"DATABASE_URL is required for {settings.app_mode} mode")
        
        if settings.app_mode in [AppMode.DEVELOPMENT, AppMode.DEV]:
            if not settings.rindexer_database_url:
                raise ValueError("RINDEXER_DATABASE_URL is required for development mode")
    
    # Validate network configurations
    if not is_mock_mode():
        enabled_networks = get_enabled_networks()
        for network_name in enabled_networks:
            if network_name not in SUPPORTED_NETWORKS:
                raise ValueError(f"Unknown network '{network_name}' in NETWORKS_ENABLED")
            
            network_config = get_network_config(network_name)
            if not network_config.get("rpc_url"):
                raise ValueError(f"RPC URL is required for network '{network_name}'")


# Validate on import
validate_settings()