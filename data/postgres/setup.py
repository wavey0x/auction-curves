#!/usr/bin/env python3
"""
PostgreSQL database setup and migration script for Auction House.
"""

import os
import asyncio
import asyncpg
from pathlib import Path
from typing import Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database setup, migrations, and connections"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
    
    async def create_database(self, db_name: str):
        """Create database if it doesn't exist"""
        # Connect to default postgres database to create new one
        base_url = self.database_url.rsplit('/', 1)[0]
        conn = await asyncpg.connect(f"{base_url}/postgres")
        
        try:
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"Created database: {db_name}")
            else:
                logger.info(f"Database already exists: {db_name}")
                
        finally:
            await conn.close()
    
    async def run_migration(self, migration_file: Path):
        """Run a single migration file"""
        logger.info(f"Running migration: {migration_file.name}")
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(sql)
            logger.info(f"Successfully applied migration: {migration_file.name}")
        except Exception as e:
            logger.error(f"Failed to apply migration {migration_file.name}: {e}")
            raise
        finally:
            await conn.close()
    
    async def run_all_migrations(self):
        """Run all pending migrations"""
        if not self.migrations_dir.exists():
            logger.warning("Migrations directory not found")
            return
        
        # Get all migration files sorted by name
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            await self.run_migration(migration_file)
    
    async def setup_database(self, db_name: str):
        """Complete database setup process"""
        logger.info("Starting database setup...")
        
        # Create database
        await self.create_database(db_name)
        
        # Run migrations
        await self.run_all_migrations()
        
        logger.info("Database setup completed successfully!")
    
    async def test_connection(self):
        """Test database connection and show info"""
        conn = await asyncpg.connect(self.database_url)
        try:
            version = await conn.fetchval("SELECT version()")
            db_name = await conn.fetchval("SELECT current_database()")
            
            logger.info(f"Connected to database: {db_name}")
            logger.info(f"PostgreSQL version: {version}")
            
            # Check for TimescaleDB
            try:
                ts_version = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
                if ts_version:
                    logger.info(f"TimescaleDB version: {ts_version}")
                else:
                    logger.warning("TimescaleDB extension not found")
            except:
                logger.warning("TimescaleDB not available")
            
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        finally:
            await conn.close()

def get_database_url() -> str:
    """Get database URL from environment or use default"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/auction"
    )

async def main():
    """Main setup function"""
    database_url = get_database_url()
    logger.info(f"Database URL: {database_url}")
    
    # Extract database name from URL
    db_name = database_url.split('/')[-1]
    
    manager = DatabaseManager(database_url)
    
    try:
        # Setup database
        await manager.setup_database(db_name)
        
        # Test connection
        success = await manager.test_connection()
        
        if success:
            logger.info("✅ Database setup completed successfully!")
        else:
            logger.error("❌ Database setup failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)