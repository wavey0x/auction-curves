#!/usr/bin/env python3
"""
Fix Checksummed Addresses Script
Checks all token_address fields in token_prices table and updates any 
non-checksummed addresses to proper EIP-55 checksummed format.
"""

import os
import sys
import psycopg2
import psycopg2.extras
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def is_checksummed(address: str) -> bool:
    """Check if an address is properly checksummed"""
    try:
        return Web3.is_checksum_address(address)
    except:
        return False

def to_checksum(address: str) -> str:
    """Convert address to checksummed format"""
    try:
        return Web3.to_checksum_address(address)
    except Exception as e:
        print(f"❌ Failed to checksum {address}: {e}")
        return address  # Return original if conversion fails

def main():
    """Check and fix all token addresses in token_prices table"""
    
    print("🚀 Starting Token Address Checksum Fix")
    
    # Database connection
    app_mode = os.getenv('APP_MODE', 'dev').lower()
    if app_mode == 'dev':
        db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5433/auction_dev')
    else:
        db_url = os.getenv('PROD_DATABASE_URL')
        
    if not db_url:
        print("❌ No database URL configured")
        return
        
    try:
        db_conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        db_conn.autocommit = True
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    try:
        with db_conn.cursor() as cursor:
            # Get all unique token addresses
            print("🔍 Checking all token addresses in token_prices...")
            cursor.execute("""
                SELECT DISTINCT token_address, COUNT(*) as record_count
                FROM token_prices 
                GROUP BY token_address
                ORDER BY record_count DESC
            """)
            
            addresses = cursor.fetchall()
            print(f"📊 Found {len(addresses)} unique token addresses")
            
            # Check each address
            fixes_needed = []
            for addr_info in addresses:
                address = addr_info['token_address']
                record_count = addr_info['record_count']
                
                if not is_checksummed(address):
                    checksummed = to_checksum(address)
                    if checksummed != address:
                        fixes_needed.append({
                            'original': address,
                            'checksummed': checksummed,
                            'count': record_count
                        })
            
            if not fixes_needed:
                print("✅ All token addresses are already properly checksummed!")
                return
            
            print(f"\n🔧 Found {len(fixes_needed)} addresses needing checksum fixes:")
            total_records = 0
            for fix in fixes_needed:
                print(f"   {fix['original']} → {fix['checksummed']} ({fix['count']} records)")
                total_records += fix['count']
            
            print(f"\n📊 Total records to update: {total_records}")
            print("\n🔄 Proceeding with automatic update...")
            
            # Apply fixes
            print("\n🔄 Applying checksum fixes...")
            success_count = 0
            failure_count = 0
            
            for i, fix in enumerate(fixes_needed, 1):
                original = fix['original']
                checksummed = fix['checksummed']
                count = fix['count']
                
                try:
                    cursor.execute("""
                        UPDATE token_prices 
                        SET token_address = %s
                        WHERE token_address = %s
                    """, (checksummed, original))
                    
                    updated_rows = cursor.rowcount
                    if updated_rows == count:
                        print(f"✅ {i}/{len(fixes_needed)}: Updated {updated_rows} records for {original}")
                        success_count += updated_rows
                    else:
                        print(f"⚠️  {i}/{len(fixes_needed)}: Expected {count} but updated {updated_rows} records for {original}")
                        success_count += updated_rows
                        
                except Exception as e:
                    print(f"❌ {i}/{len(fixes_needed)}: Failed to update {original}: {e}")
                    failure_count += count
            
            # Final summary
            print(f"\n✅ Checksum Fix Complete!")
            print(f"📊 Summary:")
            print(f"   • Addresses fixed: {len(fixes_needed)}")
            print(f"   • Records updated: {success_count}")
            if failure_count > 0:
                print(f"   • Failed updates: {failure_count}")
            
            # Verify the fixes
            print(f"\n🔍 Verifying fixes...")
            cursor.execute("""
                SELECT DISTINCT token_address
                FROM token_prices 
                ORDER BY token_address
                LIMIT 10
            """)
            
            sample_addresses = cursor.fetchall()
            all_good = True
            for addr_info in sample_addresses:
                address = addr_info['token_address']
                if not is_checksummed(address):
                    print(f"⚠️  Still not checksummed: {address}")
                    all_good = False
            
            if all_good:
                print("✅ Verification passed - sample addresses are all checksummed")
            else:
                print("❌ Some addresses still need fixing")
                
    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_conn.close()
        print("👋 Database connection closed")

if __name__ == '__main__':
    main()