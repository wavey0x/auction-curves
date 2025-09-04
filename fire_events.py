#!/usr/bin/env python3
"""
Interactive Redis Event Firing Script
=====================================
Fire various auction events to Redis streams for testing consumers like Telegram bot.
Supports interactive mode, batch mode, and realistic event sequences.
"""
import redis
import json
import time
import sys
import os
import random
from datetime import datetime
from typing import Dict, List, Optional

class EventFirer:
    """Interactive Redis event firing tool"""
    
    def __init__(self, redis_url: str = None):
        # Build URL with optional auth; prefer publisher role
        if not redis_url:
            try:
                from scripts.lib.redis_utils import build_redis_url
                redis_url = build_redis_url(role='publisher')
            except Exception:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_url = redis_url
        self.redis = None
        self.connect()
        
        # Pre-defined realistic data for variety
        self.sample_addresses = {
            'auctions': [
                '0x1234567890123456789012345678901234567890',
                '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd',
                '0x9876543210987654321098765432109876543210',
                '0xfedcbafedcbafedcbafedcbafedcbafedcbafedcb',
            ],
            'takers': [
                '0xtaker1234567890123456789012345678901234',
                '0xwhale9876543210987654321098765432109876',
                '0xbot45678901234567890123456789012345678',
                '0xtrader1234567890123456789012345678901',
            ],
            'tokens': [
                '0xwanttoken1234567890123456789012345678',
                '0xhavetoken9876543210987654321098765432',
                '0xusdc123456789012345678901234567890123',
                '0xweth987654321098765432109876543210987',
            ]
        }
        
        self.chains = {
            1: 'Ethereum',
            137: 'Polygon', 
            42161: 'Arbitrum',
            10: 'Optimism',
            8453: 'Base',
            31337: 'Local'
        }
    
    def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=5,
            )
            self.redis.ping()
            # Mask credentials in printed URL
            safe_url = self.redis_url
            if '@' in safe_url:
                safe_url = safe_url.replace(safe_url.split('://',1)[1].split('@',1)[0], '***')
            print(f"✅ Connected to Redis at {safe_url}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("   Make sure Redis is running: docker-compose up -d redis")
            sys.exit(1)
    
    def fire_deploy_event(self, chain_id: int = 31337, custom_data: Dict = None) -> str:
        """Fire a deployment event"""
        auction_addr = custom_data.get('auction_address') if custom_data else random.choice(self.sample_addresses['auctions'])
        want_token = custom_data.get('want_token') if custom_data else random.choice(self.sample_addresses['tokens'])
        
        event = {
            'id': f'deploy-{int(time.time())}-{random.randint(1000, 9999)}',
            'type': 'deploy',
            'chain_id': chain_id,
            'auction_address': auction_addr,
            'tx_hash': f'0x{"".join(random.choices("abcdef0123456789", k=64))}',
            'block_number': random.randint(1000, 9999),
            'payload_json': json.dumps({
                'deployer': f'0x{"".join(random.choices("abcdef0123456789", k=40))}',
                'version': random.choice(['0.1.0', '0.2.0', '1.0.0']),
                'want_token': want_token,
                'starting_price': str(random.randint(1, 10) * 10**18),  # 1-10 tokens
                'decay_rate': '0.005',  # 0.5% decay
                'update_interval': random.choice([300, 600, 900])  # 5, 10, or 15 minutes
            })
        }
        
        return self._send_event(event)
    
    def fire_kick_event(self, chain_id: int = 31337, auction_addr: str = None, custom_data: Dict = None) -> str:
        """Fire a kick (round start) event"""
        auction_addr = auction_addr or (custom_data.get('auction_address') if custom_data else random.choice(self.sample_addresses['auctions']))
        round_id = custom_data.get('round_id') if custom_data else random.randint(1, 100)
        
        event = {
            'id': f'kick-{int(time.time())}-{random.randint(1000, 9999)}',
            'type': 'kick',
            'chain_id': chain_id,
            'auction_address': auction_addr,
            'round_id': round_id,
            'from_token': random.choice(self.sample_addresses['tokens']),
            'tx_hash': f'0x{"".join(random.choices("abcdef0123456789", k=64))}',
            'block_number': random.randint(1000, 9999),
            'payload_json': json.dumps({
                'kicker': random.choice(self.sample_addresses['takers']),
                'round_id': round_id,
                'initial_available': str(random.randint(10, 1000) * 10**18),  # 10-1000 tokens
                'initial_available_usd': round(random.uniform(1000, 50000), 2),
                'want_token': random.choice(self.sample_addresses['tokens']),
                'have_token': random.choice(self.sample_addresses['tokens']),
                'auction_length': random.choice([3600, 7200, 14400])  # 1, 2, or 4 hours
            })
        }
        
        return self._send_event(event)
    
    def fire_take_event(self, value_tier: str = 'normal', chain_id: int = 31337, 
                       auction_addr: str = None, round_id: int = None, custom_data: Dict = None) -> str:
        """Fire a take event with specified value tier"""
        
        # Value tiers for realistic testing
        value_configs = {
            'micro': {'min_usd': 10, 'max_usd': 100, 'emoji': '🔸'},
            'small': {'min_usd': 100, 'max_usd': 1000, 'emoji': '💰'},
            'normal': {'min_usd': 1000, 'max_usd': 10000, 'emoji': '💵'},
            'large': {'min_usd': 10000, 'max_usd': 50000, 'emoji': '💎'},
            'whale': {'min_usd': 50000, 'max_usd': 500000, 'emoji': '🐋'},
            'megawhale': {'min_usd': 500000, 'max_usd': 2000000, 'emoji': '🚀'}
        }
        
        config = value_configs.get(value_tier, value_configs['normal'])
        usd_value = round(random.uniform(config['min_usd'], config['max_usd']), 2)
        
        auction_addr = auction_addr or (custom_data.get('auction_address') if custom_data else random.choice(self.sample_addresses['auctions']))
        round_id = round_id or (custom_data.get('round_id') if custom_data else random.randint(1, 50))
        
        # Convert USD to token amounts (assuming ~$1 per token for simplicity)
        amount_taken = str(int(usd_value * 10**18))
        amount_paid = str(int(usd_value * 0.98 * 10**18))  # 2% slippage
        
        event = {
            'id': f'take-{int(time.time())}-{random.randint(1000, 9999)}',
            'type': 'take',
            'chain_id': chain_id,
            'auction_address': auction_addr,
            'round_id': round_id,
            'from_token': random.choice(self.sample_addresses['tokens']),
            'want_token': random.choice(self.sample_addresses['tokens']),
            'tx_hash': f'0x{"".join(random.choices("abcdef0123456789", k=64))}',
            'block_number': random.randint(1000, 9999),
            'payload_json': json.dumps({
                'taker': random.choice(self.sample_addresses['takers']),
                'amount_taken': amount_taken,
                'amount_paid': amount_paid,
                'amount_taken_usd': usd_value,
                'amount_paid_usd': usd_value * 0.98,
                'want_token': random.choice(self.sample_addresses['tokens']),
                'have_token': random.choice(self.sample_addresses['tokens']),
                'percentage_complete': round(random.uniform(5, 95), 1),
                'seconds_from_round_start': random.randint(60, 3600),
                'sale_id': random.randint(1, 10)
            })
        }
        
        return self._send_event(event)
    
    def fire_sequence(self, auction_addr: str = None, chain_id: int = 31337, rounds: int = 3) -> List[str]:
        """Fire a realistic sequence: deploy -> kick -> takes -> kick -> takes..."""
        results = []
        
        # Use provided auction or generate one
        if not auction_addr:
            auction_addr = random.choice(self.sample_addresses['auctions'])
        
        print(f"🎬 Starting event sequence for auction {auction_addr[:8]}... on {self.chains.get(chain_id, f'Chain {chain_id}')}")
        
        # 1. Deploy
        print("  1️⃣ Deploying auction...")
        deploy_id = self.fire_deploy_event(chain_id, {'auction_address': auction_addr})
        results.append(f"Deploy: {deploy_id}")
        time.sleep(1)
        
        # 2. Multiple rounds
        for round_num in range(1, rounds + 1):
            print(f"  {round_num + 1}️⃣ Round {round_num}: Kick + Takes...")
            
            # Kick
            kick_id = self.fire_kick_event(chain_id, auction_addr, {'round_id': round_num})
            results.append(f"Kick R{round_num}: {kick_id}")
            time.sleep(0.5)
            
            # Multiple takes per round
            num_takes = random.randint(2, 6)
            for take_num in range(num_takes):
                # Mix of value tiers for realism
                tier = random.choices(['micro', 'small', 'normal', 'large', 'whale'], 
                                    weights=[20, 30, 30, 15, 5])[0]
                take_id = self.fire_take_event(tier, chain_id, auction_addr, round_num)
                results.append(f"Take R{round_num}.{take_num+1} ({tier}): {take_id}")
                time.sleep(0.3)
        
        print(f"✅ Sequence complete! Fired {len(results)} events")
        return results
    
    def fire_stress_test(self, duration_seconds: int = 30, events_per_second: float = 2.0) -> List[str]:
        """Fire events continuously for stress testing"""
        results = []
        end_time = time.time() + duration_seconds
        delay = 1.0 / events_per_second
        
        print(f"🔥 Starting stress test: {events_per_second} events/sec for {duration_seconds}s")
        
        while time.time() < end_time:
            # Random event type
            event_type = random.choices(['deploy', 'kick', 'take'], weights=[10, 20, 70])[0]
            
            if event_type == 'deploy':
                event_id = self.fire_deploy_event(random.choice([1, 137, 42161, 31337]))
            elif event_type == 'kick':
                event_id = self.fire_kick_event(random.choice([1, 137, 42161, 31337]))
            else:  # take
                tier = random.choices(['micro', 'small', 'normal', 'large', 'whale'], 
                                    weights=[25, 35, 25, 10, 5])[0]
                event_id = self.fire_take_event(tier, random.choice([1, 137, 42161, 31337]))
            
            results.append(f"{event_type}: {event_id}")
            time.sleep(delay)
        
        print(f"✅ Stress test complete! Fired {len(results)} events")
        return results
    
    def _send_event(self, event: Dict) -> str:
        """Send event to Redis stream"""
        try:
            stream_id = self.redis.xadd('events', event)
            chain_name = self.chains.get(event['chain_id'], f"Chain {event['chain_id']}")
            print(f"  📡 {event['type'].upper()}: {stream_id} ({chain_name})")
            return stream_id
        except Exception as e:
            print(f"  ❌ Failed to send {event['type']} event: {e}")
            try:
                # Show quick stream info to help debug perms
                info = self.redis.xinfo_stream('events')
                print(f"  ℹ️  Stream length={info.get('length')} last-id={info.get('last-generated-id')}")
            except Exception as ee:
                print(f"  ℹ️  Could not fetch stream info: {ee}")
            return None
    
    def interactive_menu(self):
        """Interactive command-line menu"""
        while True:
            print("\n" + "="*60)
            print("🔥 REDIS EVENT FIRER")
            print("="*60)
            print("Single Events:")
            print("  1. Deploy event")
            print("  2. Kick event") 
            print("  3. Take event (normal)")
            print("  4. Take event (whale)")
            print("  5. Take event (custom value)")
            print("\nSequences:")
            print("  6. Realistic sequence (deploy + rounds)")
            print("  7. Multi-chain sequence")
            print("  8. Stress test")
            print("\nUtilities:")
            print("  9. Stream info")
            print("  0. Exit")
            
            choice = input("\n🎯 Choice: ").strip()
            
            if choice == '0':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                chain = self._get_chain_input()
                self.fire_deploy_event(chain)
            elif choice == '2':
                chain = self._get_chain_input()
                self.fire_kick_event(chain)
            elif choice == '3':
                chain = self._get_chain_input()
                self.fire_take_event('normal', chain)
            elif choice == '4':
                chain = self._get_chain_input()
                self.fire_take_event('whale', chain)
            elif choice == '5':
                chain = self._get_chain_input()
                tier = input("Value tier (micro/small/normal/large/whale/megawhale): ").strip()
                self.fire_take_event(tier if tier else 'normal', chain)
            elif choice == '6':
                chain = self._get_chain_input()
                rounds = input("Number of rounds (default 3): ").strip()
                rounds = int(rounds) if rounds.isdigit() else 3
                self.fire_sequence(chain_id=chain, rounds=rounds)
            elif choice == '7':
                chains = [1, 137, 42161, 31337]
                for chain in chains:
                    print(f"\n🌐 Firing sequence on {self.chains[chain]}...")
                    self.fire_sequence(chain_id=chain, rounds=2)
                    time.sleep(2)
            elif choice == '8':
                duration = input("Duration in seconds (default 30): ").strip()
                rate = input("Events per second (default 2.0): ").strip()
                duration = int(duration) if duration.isdigit() else 30
                rate = float(rate) if rate.replace('.','').isdigit() else 2.0
                self.fire_stress_test(duration, rate)
            elif choice == '9':
                self._show_stream_info()
            else:
                print("❌ Invalid choice")
    
    def _get_chain_input(self) -> int:
        """Get chain ID from user input"""
        print("Chains: 1=Ethereum, 137=Polygon, 42161=Arbitrum, 10=Optimism, 8453=Base, 31337=Local")
        chain_input = input("Chain ID (default 31337): ").strip()
        return int(chain_input) if chain_input.isdigit() else 31337
    
    def _show_stream_info(self):
        """Show Redis stream information"""
        try:
            info = self.redis.xinfo_stream('events')
            print(f"\n📊 Stream 'events' info:")
            print(f"   Length: {info.get('length', 0)} messages")
            print(f"   Groups: {info.get('groups', 0)}")
            print(f"   Last ID: {info.get('last-generated-id', 'N/A')}")
            
            # Show recent messages
            messages = self.redis.xrevrange('events', count=5)
            print(f"\n📝 Recent messages:")
            for msg_id, data in messages:
                event_type = data.get('type', 'unknown')
                chain_id = data.get('chain_id', 'N/A')
                chain_name = self.chains.get(int(chain_id) if str(chain_id).isdigit() else 0, f'Chain {chain_id}')
                print(f"   {msg_id}: {event_type.upper()} on {chain_name}")
                
        except Exception as e:
            print(f"❌ Error getting stream info: {e}")


def main():
    """Main entry point"""
    print("🔥 Redis Event Firer - Test Consumer Downstream Actions")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        # Command line mode
        command = sys.argv[1].lower()
        firer = EventFirer()
        
        if command == 'deploy':
            firer.fire_deploy_event()
        elif command == 'kick':
            firer.fire_kick_event()
        elif command == 'take':
            tier = sys.argv[2] if len(sys.argv) > 2 else 'normal'
            firer.fire_take_event(tier)
        elif command == 'sequence':
            rounds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 3
            firer.fire_sequence(rounds=rounds)
        elif command == 'stress':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
            rate = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
            firer.fire_stress_test(duration, rate)
        else:
            print("Usage: python3 fire_events.py [deploy|kick|take|sequence|stress] [args...]")
            print("   or: python3 fire_events.py  # for interactive mode")
    else:
        # Interactive mode
        firer = EventFirer()
        firer.interactive_menu()


if __name__ == '__main__':
    main()
