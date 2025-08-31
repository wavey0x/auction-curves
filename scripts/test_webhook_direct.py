#!/usr/bin/env python3
"""
Manual webhook testing script with correct Rindexer payload structure.
Tests webhook processing with various payload formats.
"""

import requests
import json
import sys


API_BASE = "http://localhost:8000"


def test_debug_endpoint():
    """Test the debug endpoint with various payload structures"""
    
    print("🧪 Testing Debug Endpoint")
    print("=" * 50)
    
    # Test 1: Manual test format (flat structure)
    print("\n📋 Test 1: Manual/Flat Structure")
    manual_payload = {
        "event_name": "AuctionKicked",
        "contract_address": "0xb7a5bd0345ef1cc5e66bf61bdec17d2461fbd968",
        "from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
        "available": "1000000000",
        "tx_hash": "0x0196b694dca2a5e02a6300a417af6dea3a6043da5e5bd2af1df27bf98a9d40d9",
        "block_number": 49,
        "network": "local"
    }
    
    response = requests.post(f"{API_BASE}/webhook/test-debug", json=manual_payload)
    print_response("Manual Structure", response)
    
    # Test 2: Rindexer format (nested structure)
    print("\n📋 Test 2: Rindexer Nested Structure")
    rindexer_payload = {
        "event_name": "AuctionKicked",
        "event_signature_hash": "0x1234567890abcdef",
        "event_data": {
            "from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
            "available": "1000000000",
            "transaction_information": {
                "address": "0xb7a5bd0345ef1cc5e66bf61bdec17d2461fbd968",
                "block_hash": "0x7702e258992462062baedb8f3c64f3bdba5b395cf1b04e56dee83910de7e9f3b",
                "block_number": "49",
                "log_index": "0",
                "network": "local",
                "transaction_hash": "0x0196b694dca2a5e02a6300a417af6dea3a6043da5e5bd2af1df27bf98a9d40d9",
                "transaction_index": "0"
            }
        },
        "network": "local"
    }
    
    response = requests.post(f"{API_BASE}/webhook/test-debug", json=rindexer_payload)
    print_response("Rindexer Structure", response)
    
    # Test 3: Missing fields
    print("\n📋 Test 3: Missing Required Fields")
    incomplete_payload = {
        "event_name": "AuctionKicked",
        "event_data": {
            "available": "1000000000",
            "transaction_information": {
                "block_number": "49",
                "network": "local"
            }
        }
    }
    
    response = requests.post(f"{API_BASE}/webhook/test-debug", json=incomplete_payload)
    print_response("Incomplete Structure", response)


def test_real_webhook():
    """Test the real webhook endpoint"""
    
    print("\n🚀 Testing Real Webhook Endpoint")
    print("=" * 50)
    
    # Test with Rindexer format
    print("\n📋 Test: Real Webhook with Rindexer Structure")
    rindexer_payload = {
        "event_name": "AuctionKicked", 
        "event_signature_hash": "0x1234567890abcdef",
        "event_data": {
            "from": "0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0",
            "available": "1000000000",
            "transaction_information": {
                "address": "0xb7a5bd0345ef1cc5e66bf61bdec17d2461fbd968",
                "block_hash": "0x7702e258992462062baedb8f3c64f3bdba5b395cf1b04e56dee83910de7e9f3b",
                "block_number": "49",
                "log_index": "0", 
                "network": "local",
                "transaction_hash": "0x0196b694dca2a5e02a6300a417af6dea3a6043da5e5bd2af1df27bf98a9d40d9",
                "transaction_index": "0"
            }
        },
        "network": "local"
    }
    
    response = requests.post(f"{API_BASE}/webhook/process-event", json=rindexer_payload)
    print_response("Real Webhook", response)
    

def print_response(test_name, response):
    """Print formatted response"""
    print(f"\n📄 {test_name} Response:")
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        print("JSON Response:")
        print(json.dumps(data, indent=2))
        
        # Highlight important fields
        if "extracted_fields" in data:
            extracted = data["extracted_fields"]
            print(f"\n🔍 Key Extracted Fields:")
            print(f"  auction_address: {extracted.get('auction_address', 'MISSING')}")
            print(f"  from_token: {extracted.get('from_token', 'MISSING')}")
            print(f"  available: {extracted.get('available', 'MISSING')}")
            print(f"  would_process: {data.get('would_process', 'UNKNOWN')}")
            
        if "missing_fields" in data and data["missing_fields"]:
            print(f"❌ Missing fields: {data['missing_fields']}")
            
    except Exception as e:
        print(f"Response text: {response.text}")
        print(f"Error parsing JSON: {e}")


def main():
    """Run all webhook tests"""
    print("🔬 Webhook Testing Suite")
    print("=" * 70)
    
    try:
        # Check API health
        health_response = requests.get(f"{API_BASE}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ API Health: {health_data.get('status')} (mode: {health_data.get('mode')})")
        else:
            print(f"❌ API Health check failed: {health_response.status_code}")
            return
        
        # Run tests
        test_debug_endpoint()
        test_real_webhook()
        
        print("\n" + "=" * 70)
        print("🎯 Testing Complete!")
        print("\nNext steps:")
        print("1. Check API logs for detailed processing information")
        print("2. Check database: psql postgresql://wavey@localhost:5432/auction -c 'SELECT * FROM auction_rounds;'")
        print("3. Run test pipeline: python scripts/test_pipeline.py")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Is it running on port 8000?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()