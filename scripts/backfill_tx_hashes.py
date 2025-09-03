#!/usr/bin/env python3
"""
Script to backfill transaction hashes with proper 0x prefix.

This script will:
1. Update all transaction_hash fields in the 'rounds' table to add '0x' prefix if missing
2. Update all transaction_hash fields in the 'takes' table to add '0x' prefix if missing
3. Update all enabled_at_tx_hash fields in the 'enabled_tokens' table to add '0x' prefix if missing

Usage:
    python3 backfill_tx_hashes.py
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from environment variables"""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    
    # Fallback to individual parameters
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5433'),
        database=os.getenv('DB_NAME', 'auction_dev'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )

def backfill_table_tx_hashes(cursor, table_name, column_name):
    """Backfill transaction hashes for a specific table and column"""
    logger.info(f"Processing {table_name}.{column_name}...")
    
    # Count records that need updating
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM {table_name} 
        WHERE {column_name} IS NOT NULL 
        AND {column_name} NOT LIKE '0x%'
        AND LENGTH({column_name}) = 64
    """)
    count = cursor.fetchone()[0]
    
    if count == 0:
        logger.info(f"✅ No records to update in {table_name}.{column_name}")
        return 0
    
    logger.info(f"🔄 Found {count} records in {table_name}.{column_name} that need '0x' prefix")
    
    # Update records to add 0x prefix
    cursor.execute(f"""
        UPDATE {table_name} 
        SET {column_name} = '0x' || {column_name}
        WHERE {column_name} IS NOT NULL 
        AND {column_name} NOT LIKE '0x%'
        AND LENGTH({column_name}) = 64
    """)
    
    updated = cursor.rowcount
    logger.info(f"✅ Updated {updated} records in {table_name}.{column_name}")
    return updated

def main():
    """Main execution function"""
    logger.info("🚀 Starting transaction hash backfill script")
    
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_updated = 0
        
        # Backfill tables with transaction hash columns
        tables_to_update = [
            ('rounds', 'transaction_hash'),
            ('takes', 'transaction_hash'),
            ('enabled_tokens', 'enabled_at_tx_hash')
        ]
        
        for table_name, column_name in tables_to_update:
            try:
                updated = backfill_table_tx_hashes(cursor, table_name, column_name)
                total_updated += updated
            except Exception as e:
                logger.error(f"❌ Error updating {table_name}.{column_name}: {e}")
                # Continue with other tables
                continue
        
        # Commit changes
        conn.commit()
        logger.info(f"🎉 Successfully updated {total_updated} total transaction hash records")
        
        # Verify updates
        logger.info("🔍 Verifying updates...")
        for table_name, column_name in tables_to_update:
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE {column_name} IS NOT NULL 
                    AND {column_name} NOT LIKE '0x%'
                    AND LENGTH({column_name}) = 64
                """)
                remaining = cursor.fetchone()[0]
                
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {table_name} 
                    WHERE {column_name} LIKE '0x%'
                    AND LENGTH({column_name}) = 66
                """)
                with_prefix = cursor.fetchone()[0]
                
                if remaining == 0:
                    logger.info(f"✅ {table_name}.{column_name}: {with_prefix} records now have proper '0x' prefix")
                else:
                    logger.warning(f"⚠️  {table_name}.{column_name}: {remaining} records still missing '0x' prefix")
                    
            except Exception as e:
                logger.error(f"❌ Error verifying {table_name}.{column_name}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return 1
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    
    logger.info("🏁 Transaction hash backfill script completed")
    return 0

if __name__ == '__main__':
    sys.exit(main())