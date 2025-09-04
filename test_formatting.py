#!/usr/bin/env python3
"""
Test script to consume Redis events and show formatted messages
without requiring Telegram dependencies
"""
import os
import sys
import json
import time
import yaml
import redis
import psycopg2
from decimal import Decimal
from typing import Dict, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FormatTester:
    """Test the Telegram formatting without actual Telegram API"""
    
    def __init__(self, config_path: str = "scripts/telegram_config.yaml"):
        # Load configuration
        self.config = self._load_config(config_path)
        self.redis_client = None
        self.db_conn = None
        self.token_cache = {}
        
        # Initialize Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Initialize database connection for token info
        try:
            db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://wavey@localhost:5432/auction_dev')
            self.db_conn = psycopg2.connect(db_url)
        except Exception as e:
            print(f"⚠️ Warning: Could not connect to database: {e}")
            print("   Token symbols will show as 'TOKEN'")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_content = f.read()
                
            # Expand environment variables
            import re
            def replace_env_vars(match):
                var_expr = match.group(1)
                # Handle fallback syntax ${VAR1:-${VAR2}}
                if ':-' in var_expr:
                    primary, fallback = var_expr.split(':-', 1)
                    primary = primary.strip()
                    if fallback.startswith('${') and fallback.endswith('}'):
                        fallback = fallback[2:-1]
                    return os.getenv(primary) or os.getenv(fallback, '')
                else:
                    return os.getenv(var_expr, '')
            
            config_content = re.sub(r'\\$\\{([^}]+)\\}', replace_env_vars, config_content)
            return yaml.safe_load(config_content)
            
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration"""
        return {
            'groups': {
                'dev_alerts': {
                    'description': 'Development alerts',
                    'events': {'deploy': True, 'kick': True, 'take': True},
                    'filters': {'min_take_usd': 0, 'enabled_chains': [31337]},
                    'thresholds': {'large_take_usd': 1000, 'whale_take_usd': 10000},
                    'formatting': {'show_usd_values': True, 'use_token_symbols': True, 'decimal_places': 2}
                }
            },
            'global': {
                'chains': {1: 'Ethereum', 137: 'Polygon', 42161: 'Arbitrum', 31337: 'Local'},
                'explorers': {1: 'https://etherscan.io/tx/', 31337: None},
                'app_urls': {
                    'auction_details': '/auction/{address}',
                    'round_details': '/round/{auction_address}/{round_id}',
                    'taker_details': '/taker/{address}'
                }
            }
        }
    
    def _get_token_info(self, token_address: str, chain_id: int) -> Dict:
        """Get token info from database"""
        if not self.db_conn:
            return {}
            
        cache_key = f"{token_address}_{chain_id}"
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT symbol, decimals FROM tokens WHERE LOWER(address) = LOWER(%s) AND chain_id = %s",
                    (token_address, chain_id)
                )
                result = cursor.fetchone()
                if result:
                    token_info = {'symbol': result[0], 'decimals': result[1]}
                else:
                    token_info = {}
                
                self.token_cache[cache_key] = token_info
                return token_info
        except Exception:
            return {}
    
    # Include all the formatting methods from telegram_bot.py
    def _format_amount(self, amount_str: str, decimals: int = 18) -> str:
        """Format token amount with proper decimals - convert from wei if needed"""
        try:
            if not amount_str or amount_str == 'N/A':
                return 'N/A'
            
            amount = Decimal(str(amount_str))
            if amount == 0:
                return "0"
            
            # Check if this looks like a wei amount (very large number)
            # If the amount is > 1e12, likely in wei and needs conversion
            if amount > 1e12:
                # Convert from wei (assuming 18 decimals for most tokens)
                amount = amount / Decimal(10 ** decimals)
            
            # Format based on size
            if amount < 1:
                return f"{amount:.6f}".rstrip('0').rstrip('.')
            elif amount < 100:
                return f"{amount:.4f}".rstrip('0').rstrip('.')
            elif amount < 10000:
                return f"{amount:,.2f}"
            else:
                return f"{amount:,.0f}"
                
        except (ValueError, TypeError, ArithmeticError):
            return str(amount_str)
    
    def _format_usd(self, usd_value: str) -> str:
        """Format USD value with proper thousands separators"""
        try:
            if not usd_value or usd_value == 'N/A' or usd_value is None:
                return ""
                
            value = float(usd_value)
            if value == 0:
                return ""
                
            if value >= 1000000:
                return f"${value/1000000:,.1f}M"
            elif value >= 1000:
                return f"${value:,.0f}"
            else:
                return f"${value:,.2f}"
                
        except (ValueError, TypeError):
            return ""
    
    def _format_duration(self, seconds: int) -> str:
        """Format seconds into human readable duration"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}m {remaining_seconds}s"
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours}h {remaining_minutes}m"
            return f"{hours}h"
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for MarkdownV2"""
        if not isinstance(text, str):
            text = str(text)
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def _get_base_url(self) -> str:
        """Get base URL for the application"""
        # For testing, use localhost
        return "http://localhost:3000"
    
    def _get_app_link(self, template: str, **kwargs) -> str:
        """Generate internal application link"""
        base_url = self._get_base_url()
        app_urls = self.config.get('global', {}).get('app_urls', {})
        
        if template in app_urls:
            path = app_urls[template].format(**kwargs)
            return f"{base_url}{path}"
        
        return base_url
    
    def _get_explorer_link(self, tx_hash: str, chain_id: int) -> Optional[str]:
        """Generate blockchain explorer link for transaction"""
        if not tx_hash or tx_hash == 'N/A':
            return None
            
        explorers = self.config.get('global', {}).get('explorers', {})
        explorer_base = explorers.get(chain_id)
        
        if explorer_base:
            return f"{explorer_base}{tx_hash}"
        return None
    
    def _get_address_explorer_link(self, address: str, chain_id: int) -> Optional[str]:
        """Generate blockchain explorer link for address"""
        if not address or address == 'N/A' or chain_id == 31337:  # No explorer for local chain
            return None
            
        explorers = self.config.get('global', {}).get('explorers', {})
        explorer_base = explorers.get(chain_id)
        
        if explorer_base:
            # Replace /tx/ with /address/ for address links
            address_base = explorer_base.replace('/tx/', '/address/')
            return f"{address_base}{address}"
        return None
    
    def _format_markdown_link(self, text: str, url: str) -> str:
        """Format a clickable link in Telegram MarkdownV2"""
        # Escape special characters for MarkdownV2
        def escape_markdown(text: str) -> str:
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text
        
        escaped_text = escape_markdown(text)
        return f"[{escaped_text}]({url})"
    
    def _format_address_with_links(self, address: str, chain_id: int, address_type: str = 'address', internal_link: str = None) -> str:
        """Format address with both internal and external links - ensure addresses are always hyperlinked"""
        if not address or address == 'N/A':
            return 'N/A'
            
        # Short address for display
        short_addr = f"{address[:6]}...{address[-4:]}"
        
        # Always hyperlink addresses - never use code blocks
        if internal_link:
            primary_link = self._format_markdown_link(short_addr, internal_link)
        else:
            # If no internal link, link to explorer directly or just show address
            explorer_link = self._get_address_explorer_link(address, chain_id)
            if explorer_link and chain_id != 31337:
                primary_link = self._format_markdown_link(short_addr, explorer_link)
            else:
                # For local chain or no explorer, just show address (no code block)
                primary_link = self._escape_markdown(short_addr)
        
        # Add explorer link as secondary link (for non-local chains) if we have internal link
        if internal_link and chain_id != 31337:
            explorer_link = self._get_address_explorer_link(address, chain_id)
            if explorer_link:
                explorer_md = self._format_markdown_link("↗", explorer_link)
                return f"{primary_link} {explorer_md}"
        
        return primary_link
    
    def _format_take_event(self, event: Dict, group_config: Dict) -> str:
        """Format take event message with clean styling"""
        try:
            payload = json.loads(event.get('payload_json', '{}'))
            chain_id = int(event.get('chain_id', 0))
            chain_name = self.config.get('global', {}).get('chains', {}).get(chain_id, f"Chain {chain_id}")
            
            round_id = event.get('round_id', 'N/A')
            taker = payload.get('taker', 'N/A')
            amount_taken = payload.get('amount_taken', 'N/A')
            amount_paid = payload.get('amount_paid', 'N/A')
            seconds_from_start = payload.get('seconds_from_round_start', 0)
            
            from_token_addr = event.get('from_token', 'N/A')
            want_token_addr = event.get('want_token', 'N/A')
            
            # Get proper token symbols or fallback to generic names
            from_token_symbol = 'TOKEN'
            want_token_symbol = 'TOKEN'
            
            if group_config.get('formatting', {}).get('use_token_symbols', True):
                from_token_info = self._get_token_info(from_token_addr, chain_id) if from_token_addr != 'N/A' else {}
                want_token_info = self._get_token_info(want_token_addr, chain_id) if want_token_addr != 'N/A' else {}
                
                from_token_symbol = from_token_info.get('symbol', 'TOKEN')
                want_token_symbol = want_token_info.get('symbol', 'TOKEN')
            
            # Determine message style based on value
            usd_value = 0
            try:
                amount_usd = payload.get('amount_paid_usd') or payload.get('amount_taken_usd')
                if amount_usd:
                    usd_value = float(amount_usd)
            except (ValueError, TypeError):
                pass
            
            # Choose header based on group-specific value thresholds
            thresholds = group_config.get('thresholds', {})
            whale_threshold = thresholds.get('whale_take_usd', 100000)
            large_threshold = thresholds.get('large_take_usd', 10000)
            
            if usd_value >= whale_threshold:
                header = "🐋 *WHALE ALERT*"
            elif usd_value >= large_threshold:
                header = "💎 *LARGE TAKE*"
            else:
                header = "💰 *Take*"
            
            message = f"{header}\\n"
            
            # Taker with internal and explorer links
            if taker != 'N/A':
                taker_internal_link = self._get_app_link('taker_details', address=taker)
                taker_formatted = self._format_address_with_links(taker, chain_id, 'taker', taker_internal_link)
                message += f"Taker: {taker_formatted}\\n"
            
            # Amount taken with token symbol
            if amount_taken != 'N/A':
                formatted_taken = self._format_amount(str(amount_taken))
                usd_taken = self._format_usd(payload.get('amount_taken_usd', ''))
                message += f"Bought: {formatted_taken} {from_token_symbol}"
                if usd_taken:
                    message += f" \\\\({self._escape_markdown(usd_taken)}\\\\)"
                message += "\\n"
            
            # Amount paid with token symbol  
            if amount_paid != 'N/A':
                formatted_paid = self._format_amount(str(amount_paid))
                usd_paid = self._format_usd(payload.get('amount_paid_usd', ''))
                message += f"Paid: {formatted_paid} {want_token_symbol}"
                if usd_paid:
                    message += f" \\\\({self._escape_markdown(usd_paid)}\\\\)"
                message += "\\n"
            
            # Time elapsed
            if seconds_from_start > 0:
                elapsed_str = self._format_duration(int(seconds_from_start))
                message += f"{elapsed_str} into round\\n"
            
            # Chain and Round (with round link)
            auction_address = event.get('auction_address', 'N/A')
            if auction_address != 'N/A' and round_id != 'N/A':
                round_internal_link = self._get_app_link('round_details', auction_address=auction_address, round_id=round_id)
                round_link = self._format_markdown_link(f"Round #{round_id}", round_internal_link)
                message += f"Chain: {self._escape_markdown(chain_name)} \\\\| {round_link}\\n"
            else:
                message += f"Chain: {self._escape_markdown(chain_name)} \\\\| Round #{round_id}\\n"
            
            # Transaction link (always at bottom)
            tx_hash = event.get('tx_hash')
            if tx_hash and tx_hash != 'N/A':
                message += "\\n"
                if chain_id == 31337:  # Local chain  
                    message += f"🔗 Transaction: `{tx_hash[:8]}...{tx_hash[-6:]}`"
                else:
                    explorer_link = self._get_explorer_link(tx_hash, chain_id)
                    if explorer_link:
                        chain_name_short = chain_name.split()[0]  # "Ethereum" -> "Ethereum"
                        tx_link = self._format_markdown_link(f"View on {chain_name_short}scan", explorer_link)
                        message += f"🔗 {tx_link}"
            
            return message
            
        except Exception as e:
            print(f"Error formatting take event: {e}")
            return f"💰 *Take Executed\\!* \\(formatting error\\)"
    
    def test_latest_events(self, count: int = 5):
        """Test formatting on the latest events in Redis"""
        try:
            messages = self.redis_client.xrevrange('events', count=count)
            
            if not messages:
                print("❌ No events found in Redis stream 'events'")
                print("   Try running: python3 fire_events.py take whale")
                return
            
            print(f"🧪 Testing formatting on latest {len(messages)} events:\\n")
            
            # Get dev group config for testing
            group_config = self.config['groups']['dev_alerts']
            
            for i, (msg_id, event_data) in enumerate(messages, 1):
                event_type = event_data.get('type', 'unknown')
                print(f"{'='*60}")
                print(f"Event {i}: {event_type.upper()} ({msg_id})")
                print(f"{'='*60}")
                
                if event_type == 'take':
                    formatted = self._format_take_event(event_data, group_config)
                    # Convert escape sequences back for display
                    display_formatted = formatted.replace('\\\\n', '\\n').replace('\\\\(', '(').replace('\\\\)', ')').replace('\\\\|', '|')
                    print(display_formatted)
                else:
                    print(f"⚠️ Only take events are implemented in this test script")
                    print(f"Event data: {json.dumps(event_data, indent=2)}")
                
                print()
                
        except Exception as e:
            print(f"❌ Error testing events: {e}")

def main():
    tester = FormatTester()
    tester.test_latest_events(3)

if __name__ == '__main__':
    main()