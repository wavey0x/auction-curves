#!/usr/bin/env python3
"""
Auction House setup script.
Sets up the minimal database schema that works alongside Rindexer.
"""

import os
import asyncio
import asyncpg
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_minimal_schema():
    """Setup the minimal schema that supplements Rindexer"""
    
    database_url = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost:5432/auction"
    )
    
    logger.info("Setting up Auction House database schema...")
    logger.info(f"Database URL: {database_url}")
    
    # Read schema files
    schema_path = Path(__file__).parent / "data" / "postgres" / "schema.sql"
    analytics_path = Path(__file__).parent / "data" / "postgres" / "analytics_schema.sql"
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Run minimal schema
        logger.info("Creating minimal schema (token cache, auction parameters)...")
        with open(schema_path) as f:
            await conn.execute(f.read())
        logger.info("✅ Minimal schema created")
        
        # Run analytics schema
        logger.info("Creating analytics schema (for later use)...")
        with open(analytics_path) as f:
            await conn.execute(f.read())
        logger.info("✅ Analytics schema created")
        
        # Test connection
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Connected to: {version}")
        
        await conn.close()
        
        logger.info("\n🎉 Setup complete!")
        logger.info("\nNext steps:")
        logger.info("1. Start Rindexer to automatically create event tables")
        logger.info("2. Deploy contracts with: brownie run scripts/deploy/factory.py")
        logger.info("3. Rindexer will create tables: deployed_new_auction, auction_kicked, etc.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

async def main():
    """Main setup function"""
    success = await setup_minimal_schema()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)