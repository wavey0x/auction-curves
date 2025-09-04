#!/usr/bin/env python3
"""
Send a test event to Redis to verify Telegram bot integration
This script simulates auction events for testing the complete flow
"""
import redis
import json
import time
import sys
import os

def send_test_event(event_type='take'):
    """Send a test auction event to Redis streams"""
    try:
        # Connect to Redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Test Redis connection
        r.ping()
        print(f"✅ Connected to Redis at {redis_url}")
        
        # Create test event based on type
        if event_type == 'deploy':
            test_event = {
                'id': f'test-deploy-{int(time.time())}',
                'type': 'deploy',
                'chain_id': 31337,  # Local chain for dev group
                'auction_address': '0x1234567890123456789012345678901234567890',
                'tx_hash': '0xabcd' * 16,
                'block_number': 1000,
                'payload_json': json.dumps({
                    'deployer': '0xdeployer' + '0' * 30,
                    'version': '0.1.0',
                    'want_token': '0xwanttoken' + '0' * 30,
                    'starting_price': '1000000000000000000',  # 1 token
                    'decay_rate': '0.005',  # 0.5% decay
                    'update_interval': 300  # 5 minutes
                })
            }
            
        elif event_type == 'kick':
            test_event = {
                'id': f'test-kick-{int(time.time())}',
                'type': 'kick',
                'chain_id': 31337,  # Local chain
                'auction_address': '0x1234567890123456789012345678901234567890',
                'round_id': 42,
                'tx_hash': '0xkick' * 16,
                'block_number': 1001,
                'payload_json': json.dumps({
                    'kicker': '0xkicker' + '0' * 32,
                    'round_id': 42,
                    'initial_available': '50000000000000000000',  # 50 tokens
                    'want_token': '0xwanttoken' + '0' * 30,
                    'have_token': '0xhavetoken' + '0' * 30
                })
            }
            
        elif event_type == 'take':
            # Create different value tiers for testing
            value_tier = sys.argv[2] if len(sys.argv) > 2 else 'normal'
            
            if value_tier == 'whale':
                amount_usd = 150000.75  # Whale tier
                amount_taken = '150000750000000000000000'  # 150k tokens
                amount_paid = '150000000000000000000'     # 150 tokens
            elif value_tier == 'large':
                amount_usd = 25000.50   # Large tier  
                amount_taken = '25000500000000000000000'  # 25k tokens
                amount_paid = '25000000000000000000'     # 25 tokens
            else:
                amount_usd = 1000.50    # Normal tier
                amount_taken = '1000500000000000000000'  # 1k tokens  
                amount_paid = '1000000000000000000'     # 1 token
                
            test_event = {
                'id': f'test-take-{int(time.time())}',
                'type': 'take',
                'chain_id': 31337,  # Local chain for dev group
                'auction_address': '0x1234567890123456789012345678901234567890',
                'round_id': 42,
                'tx_hash': '0xtake' * 16,
                'block_number': 1002,
                'payload_json': json.dumps({
                    'taker': '0xtaker' + '0' * 34,
                    'amount_taken': amount_taken,
                    'amount_paid': amount_paid,
                    'amount_taken_usd': amount_usd,
                    'amount_paid_usd': amount_usd,
                    'want_token': '0xwanttoken' + '0' * 30,
                    'have_token': '0xhavetoken' + '0' * 30,
                    'percentage_complete': 25.5,
                    'sale_id': 1
                })
            }
        else:
            print(f"❌ Unknown event type: {event_type}")
            return False
        
        # Add to Redis stream
        stream_id = r.xadd('events', test_event)
        
        print(f"📡 Sent test {event_type} event to Redis stream 'events'")
        print(f"   Stream ID: {stream_id}")
        print(f"   Event type: {test_event['type']}")
        print(f"   Chain: {test_event['chain_id']} (Local)")
        
        if event_type == 'take':
            payload = json.loads(test_event['payload_json'])
            print(f"   USD value: ${payload['amount_taken_usd']:,.2f}")
            print(f"   Value tier: {value_tier}")
        
        print("\n📱 Check your configured Telegram groups for the alert!")
        print("   • dev_alerts group should receive this (chain_id 31337)")
        print("   • main_alerts group should receive this (no chain filter)")
        if event_type == 'take':
            if value_tier == 'whale':
                print("   • Should trigger WHALE ALERT formatting")
            elif value_tier == 'large':
                print("   • Should trigger LARGE TAKE formatting")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Make sure Redis is running: docker-compose up -d redis")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧪 Telegram Bot Test Event Sender")
    print("==================================")
    
    if len(sys.argv) < 2:
        print("Usage: python3 test_telegram_event.py <event_type> [value_tier]")
        print("\nEvent types:")
        print("  deploy  - Test auction deployment event")
        print("  kick    - Test round kick event")
        print("  take    - Test auction take event")
        print("\nValue tiers (for 'take' events only):")
        print("  normal  - Regular take ($1,000)")
        print("  large   - Large take ($25,000)")  
        print("  whale   - Whale take ($150,000)")
        print("\nExamples:")
        print("  python3 test_telegram_event.py take normal")
        print("  python3 test_telegram_event.py take whale")
        print("  python3 test_telegram_event.py deploy")
        print("  python3 test_telegram_event.py kick")
        return
    
    event_type = sys.argv[1].lower()
    
    if event_type not in ['deploy', 'kick', 'take']:
        print(f"❌ Invalid event type: {event_type}")
        print("   Valid types: deploy, kick, take")
        return
    
    success = send_test_event(event_type)
    if success:
        print("\n✅ Test event sent successfully!")
        print("   The Telegram bot should process this event within a few seconds.")
    else:
        print("\n❌ Failed to send test event")
        sys.exit(1)

if __name__ == '__main__':
    main()