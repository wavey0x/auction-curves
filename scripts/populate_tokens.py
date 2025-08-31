#!/usr/bin/env python3
"""
Token Population Script - Load tokens from deployment_info.json into database
"""

import json
import os
import psycopg2
from psycopg2.extras import DictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_deployment_data():
    """Load deployment info containing token metadata"""
    deployment_file = 'deployment_info.json'
    if not os.path.exists(deployment_file):
        raise FileNotFoundError(f"Deployment file not found: {deployment_file}")
    
    with open(deployment_file, 'r') as f:
        return json.load(f)

def get_database_connection():
    """Create database connection"""
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/auction_dev")
    try:
        conn = psycopg2.connect(database_url)
        logger.info(f"Connected to database: {database_url}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def populate_tokens(deployment_data, conn):
    """Populate tokens table from deployment data"""
    
    # Get chain_id from deployment data (defaults to 31337 for anvil)
    chain_id = 31337  # Anvil local chain
    if 'network' in deployment_data:
        if deployment_data['network'] == 'anvil':
            chain_id = 31337
    
    tokens_data = deployment_data.get('tokens', {})
    
    logger.info(f"Found {len(tokens_data)} tokens to populate")
    
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        for symbol, token_info in tokens_data.items():
            address = token_info['address']
            name = token_info['name']
            decimals = token_info['decimals']
            category = token_info.get('category', 'unknown')
            
            # Insert or update token
            cursor.execute("""
                INSERT INTO tokens (
                    address, symbol, name, decimals, chain_id, 
                    category, is_verified, first_seen, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                )
                ON CONFLICT (address, chain_id) DO UPDATE SET
                    symbol = EXCLUDED.symbol,
                    name = EXCLUDED.name,
                    decimals = EXCLUDED.decimals,
                    category = EXCLUDED.category,
                    is_verified = EXCLUDED.is_verified,
                    updated_at = NOW()
            """, (
                address, symbol, name, decimals, chain_id,
                category, True  # Mark deployment tokens as verified
            ))
            
            logger.info(f"✅ Populated token: {symbol} ({name}) at {address}")
    
    conn.commit()
    logger.info(f"✅ Successfully populated {len(tokens_data)} tokens")

def verify_tokens(conn):
    """Verify tokens were populated correctly"""
    with conn.cursor(cursor_factory=DictCursor) as cursor:
        cursor.execute("""
            SELECT address, symbol, name, decimals, category, is_verified, chain_id
            FROM tokens
            ORDER BY symbol
        """)
        
        tokens = cursor.fetchall()
        logger.info(f"Found {len(tokens)} tokens in database:")
        
        for token in tokens:
            logger.info(f"  {token['symbol']:<6} | {token['name']:<20} | {token['category']:<8} | {token['address']}")

def main():
    """Main function"""
    try:
        # Load deployment data
        deployment_data = load_deployment_data()
        logger.info(f"Loaded deployment data for network: {deployment_data.get('network', 'unknown')}")
        
        # Connect to database
        conn = get_database_connection()
        
        # Populate tokens
        populate_tokens(deployment_data, conn)
        
        # Verify results
        verify_tokens(conn)
        
        conn.close()
        logger.info("✅ Token population completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Token population failed: {e}")
        raise

if __name__ == "__main__":
    main()