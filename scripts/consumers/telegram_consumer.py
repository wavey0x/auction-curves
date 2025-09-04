#!/usr/bin/env python3
"""
Telegram bot consumer for Redis Streams events
"""
import os
import sys
import json
import time
import yaml
import asyncio
import logging
import redis
import psycopg2
import psycopg2.extras
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

try:
    from telegram import Bot
    from telegram.error import TelegramError, RetryAfter, TimedOut
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramConsumer:
    """Consumer that sends auction events to Telegram using config file"""
    
    def __init__(self, redis_url: str, config_path: str = "scripts/telegram_config.yaml", stream_key: str = 'events'):
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        if not redis_url:
            # Build URL for consumer role from env if not provided
            try:
                from scripts.lib.redis_utils import build_redis_url
                redis_url = build_redis_url(role='consumer')
            except Exception:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=5,
        )
        try:
            # Mask credentials in any logs
            safe_url = redis_url
            if isinstance(safe_url, str) and '@' in safe_url:
                safe_url = safe_url.replace(safe_url.split('://',1)[1].split('@',1)[0], '***')
            logger.info(f"✅ Connected to Redis at {safe_url}")
        except Exception:
            pass
        self.stream_key = stream_key
        self.consumer_group = 'telegram'
        self.consumer_name = f'telegram-{os.getpid()}'
        
        # Initialize Telegram bot if available and configured
        self.bot = None
        self.active_groups = {}
        self._initialize_telegram_bot()
        
        # Initialize database connection for token metadata
        self.db_conn = None
        self.token_cache = {}
        self._initialize_db_connection()
        
        self._ensure_consumer_group()

    def _normalize_tx_hash(self, tx_hash: Optional[str]) -> Optional[str]:
        """Ensure a tx hash string has 0x prefix; return None-safe."""
        if not tx_hash:
            return tx_hash
        try:
            return tx_hash if tx_hash.startswith('0x') else f'0x{tx_hash}'
        except Exception:
            return tx_hash
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load YAML and expand ${VAR} and ${VAR:-fallback} placeholders in values.

        Rules:
        - ${VAR} → env[VAR] or empty string if not set
        - ${VAR:-DEFAULT} → DEFAULT if VAR unset or empty. If DEFAULT looks like ENV_VAR_NAME, use env[DEFAULT] if set
        - Multiple placeholders in a single string are supported
        """
        try:
            with open(config_path, 'r') as f:
                raw = yaml.safe_load(f)
            expanded = self._expand_env_in_obj(raw)
            logger.info(f"Loaded configuration from {config_path}")
            return expanded
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            raise

    def _expand_env_in_obj(self, obj: Any) -> Any:
        import re
        placeholder = re.compile(r"\$\{([^}:]+)(?::-(.*?))?\}")
        env_name = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

        def replace_in_str(s: str) -> str:
            def repl(m: re.Match) -> str:
                var = m.group(1)
                fb = m.group(2)
                val = os.getenv(var)
                if val is not None and val != "":
                    return val
                if fb is None:
                    return ""
                # Support fallback specified as plain env name or nested ${ENV}
                if fb.startswith('${') and fb.endswith('}'):
                    inner = fb[2:-1]
                    return os.getenv(inner, '')
                if env_name.match(fb):
                    return os.getenv(fb, fb)
                return fb
            return placeholder.sub(repl, s)

        if isinstance(obj, dict):
            return {k: self._expand_env_in_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._expand_env_in_obj(v) for v in obj]
        if isinstance(obj, str) and "${" in obj:
            return replace_in_str(obj)
        return obj
    
    def _initialize_telegram_bot(self):
        """Initialize Telegram bot and active groups"""
        if not TELEGRAM_AVAILABLE:
            logger.info("📱 Running in TEST MODE - Telegram messages will be logged only")
            return
            
        bot_token = self.config.get('bot_token')
        if not bot_token:
            logger.info("📱 No bot_token configured - Running in TEST MODE")
            return
            
        try:
            self.bot = Bot(token=bot_token)
            logger.info("✅ Telegram bot initialized")
            
            # Initialize active groups
            for group_name, group_config in self.config.get('groups', {}).items():
                chat_id = group_config.get('chat_id')
                # Skip if chat_id is not set or empty after expansion
                if chat_id not in (None, ''):
                    try:
                        # Convert to int if it's a string that looks like a number
                        if isinstance(chat_id, str) and (chat_id.startswith('-') or chat_id.isdigit()):
                            chat_id = int(chat_id)
                        
                        self.active_groups[group_name] = {
                            'chat_id': chat_id,
                            'config': group_config,
                            'last_message_time': 0,
                            'messages_this_minute': 0,
                            'minute_start': time.time()
                        }
                        logger.info(f"✅ Configured group '{group_name}' with chat_id: {chat_id}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️  Skipping group '{group_name}': invalid chat_id '{chat_id}' - {e}")
                else:
                    logger.info(f"⚠️  Skipping group '{group_name}': chat_id not configured")
            
            if not self.active_groups:
                logger.info("📱 No valid groups configured - Running in TEST MODE")
                self.bot = None
                
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.bot = None
    
    def _initialize_db_connection(self):
        """Initialize database connection for token metadata"""
        try:
            app_mode = os.getenv('APP_MODE', 'dev')
            db_url = os.getenv(f'{app_mode.upper()}_DATABASE_URL')
            if db_url:
                self.db_conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
                logger.info("✅ Database connection established")
            else:
                logger.info("⚠️  Database URL not found, token symbols will not be resolved")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
    
    def _ensure_consumer_group(self):
        """Create consumer group if it doesn't exist"""
        try:
            # Ensure stream exists (create lazily if missing)
            try:
                self.redis_client.xinfo_stream(self.stream_key)
            except redis.ResponseError:
                # Create stream with a dummy then delete it
                dummy_id = self.redis_client.xadd(self.stream_key, {'init': 'true'})
                self.redis_client.xdel(self.stream_key, dummy_id)
                logger.info(f"Initialized Redis stream: {self.stream_key}")

            # Create group if not exists; mkstream safeguards if key was removed
            self.redis_client.xgroup_create(
                name=self.stream_key,
                groupname=self.consumer_group,
                id='$',       # start from new messages only
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group already exists: {self.consumer_group}")
            else:
                logger.error(f"Failed to create consumer group: {e}")
                raise
    
    async def _send_message_to_group(self, message: str, group_name: str, max_retries: int = 3) -> bool:
        """Send message to specific group with retry logic and group-specific rate limiting"""
        if group_name not in self.active_groups:
            logger.error(f"Group '{group_name}' not configured")
            return False
            
        group_data = self.active_groups[group_name]
        group_config = group_data['config']
        rate_config = group_config.get('rate_limiting', {})
        
        # Rate limiting check
        now = time.time()
        
        # Reset minute counter for this group
        if now - group_data['minute_start'] > 60:
            group_data['messages_this_minute'] = 0
            group_data['minute_start'] = now
            
        # Check rate limits for this group
        min_seconds = rate_config.get('min_seconds_between_messages', 1)
        time_since_last = now - group_data['last_message_time']
        if time_since_last < min_seconds:
            sleep_time = min_seconds - time_since_last
            await asyncio.sleep(sleep_time)
        
        max_per_minute = rate_config.get('max_messages_per_minute', 30)
        if group_data['messages_this_minute'] >= max_per_minute:
            logger.warning(f"Rate limit exceeded for group '{group_name}', delaying message")
            await asyncio.sleep(60 - (now - group_data['minute_start']))
            group_data['messages_this_minute'] = 0
            group_data['minute_start'] = time.time()
        
        # Send message with retries
        for attempt in range(max_retries):
            try:
                await self.bot.send_message(
                    chat_id=group_data['chat_id'],
                    text=message,
                    parse_mode='Markdown',  # Less strict than MarkdownV2
                    disable_web_page_preview=True
                )
                
                group_data['last_message_time'] = time.time()
                group_data['messages_this_minute'] += 1
                logger.info(f"📱 Message sent successfully to group '{group_name}'")
                return True
                
            except RetryAfter as e:
                wait_time = e.retry_after + 1
                logger.warning(f"Rate limited by Telegram for group '{group_name}', waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                
            except TimedOut:
                logger.warning(f"Telegram timeout for group '{group_name}', retry {attempt + 1}")
                await asyncio.sleep(2 ** attempt)
                
            except TelegramError as e:
                logger.error(f"Telegram error for group '{group_name}': {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
                
        return False
    
    async def process_event(self, event: Dict) -> bool:
        """Process single event - format and send to Telegram or log for testing"""
        try:
            event_type = event.get('type')
            
            if event_type == 'kick':
                message = self._format_kick_event(event)
            elif event_type == 'take':
                message = self._format_take_event(event)
            elif event_type == 'deploy':
                message = self._format_deploy_event(event)
            else:
                logger.debug(f"Ignoring event type: {event_type}")
                return True
            
            # If bot is configured and available, send to Telegram
            if self.bot and self.active_groups:
                sent_count = 0
                for group_name, group_data in self.active_groups.items():
                    group_config = group_data['config']
                    
                    # Check if this event should be sent to this group
                    if self._should_send_to_group(event, group_config):
                        success = await self._send_message_to_group(message, group_name)
                        if success:
                            sent_count += 1
                            logger.info(f"✅ Sent {event_type} event to group '{group_name}'")
                        else:
                            logger.error(f"❌ Failed to send {event_type} event to group '{group_name}'")
                    else:
                        logger.debug(f"Event {event_type} filtered out for group '{group_name}'")
                        
                if sent_count > 0:
                    logger.info(f"📡 Event {event_type} sent to {sent_count} group(s)")
                return True
            else:
                # Test mode - just log the formatted message
                logger.info(f"📱 TEST MODE - Formatted message:\n{message}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            return False
    
    def _should_send_to_group(self, event: Dict, group_config: Dict) -> bool:
        """Check if event should be sent to specific group based on its filters"""
        event_type = event.get('type')
        
        # Check if event type is enabled for this group
        if not group_config.get('events', {}).get(event_type, True):
            return False
        
        chain_id = int(event.get('chain_id', 0))
        filters = group_config.get('filters', {})
        
        # Check chain filter
        enabled_chains = filters.get('enabled_chains', [])
        if enabled_chains and chain_id not in enabled_chains:
            return False
        
        return True
    
    def _get_token_info(self, token_address: str, chain_id: int) -> Dict[str, str]:
        """Get token symbol and name from database"""
        cache_key = f"{chain_id}_{token_address.lower()}"
        
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        token_info = {
            'symbol': 'TOKEN',  # Generic fallback
            'name': 'Unknown Token',
            'decimals': 18
        }
        
        if self.db_conn:
            try:
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT symbol, name, decimals
                        FROM tokens 
                        WHERE LOWER(address) = LOWER(%s) AND chain_id = %s
                    """, (token_address, chain_id))
                    
                    result = cursor.fetchone()
                    if result:
                        token_info = {
                            'symbol': result['symbol'] or token_info['symbol'],
                            'name': result['name'] or token_info['name'],
                            'decimals': result['decimals'] or token_info['decimals']
                        }
            except Exception as e:
                logger.debug(f"Token lookup failed: {e}")
        
        self.token_cache[cache_key] = token_info
        return token_info
    
    def _format_amount(self, amount_str: str, decimals: int = 18) -> str:
        """Format token amount with proper decimals - convert from wei if needed"""
        try:
            if not amount_str or amount_str == 'N/A':
                return 'N/A'
            
            amount = Decimal(str(amount_str))
            if amount == 0:
                return "0"
            
            # Check if this looks like a wei amount (very large number)
            if amount > 1e12:
                amount = amount / Decimal(10 ** decimals)
            
            # Format based on size
            if amount < 1:
                formatted = f"{amount:.6f}".rstrip('0').rstrip('.')
            elif amount < 100:
                formatted = f"{amount:.4f}".rstrip('0').rstrip('.')
            elif amount < 10000:
                formatted = f"{amount:,.2f}"
            else:
                formatted = f"{amount:,.0f}"
            
            # No special escaping needed for classic Markdown numbers
            return formatted
                
        except (ValueError, TypeError, ArithmeticError):
            return str(amount_str)
    
    def _escape_markdown_v2(self, text: str) -> str:
        """Escape special characters for Telegram MarkdownV2"""
        # Characters that need escaping in MarkdownV2: _*[]()~`>#+-=|{}.!
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def _get_base_url(self) -> str:
        """Auto-detect base URL for the application"""
        env_base_url = os.getenv('APP_BASE_URL')
        if env_base_url and env_base_url.strip():
            return env_base_url.strip()
            
        # Auto-detect based on environment
        if (os.getenv('NODE_ENV') == 'development' or 
            os.getenv('APP_MODE') == 'dev' or 
            os.getenv('DEBUG') == 'true'):
            return "http://localhost:3000"
        else:
            return "https://auctions.yearn.fi"
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get readable chain name"""
        chains = {
            1: "Ethereum",
            137: "Polygon",
            42161: "Arbitrum",
            10: "Optimism",
            8453: "Base",
            31337: "Local"
        }
        return chains.get(chain_id, f"Chain {chain_id}")
    
    def _get_explorer_link(self, tx_hash: str, chain_id: int) -> Optional[str]:
        """Generate blockchain explorer link for transaction"""
        tx_hash = self._normalize_tx_hash(tx_hash) or tx_hash
        if not tx_hash or tx_hash == 'N/A' or chain_id == 31337:
            return None
            
        explorers = {
            1: "https://etherscan.io/tx/",
            137: "https://polygonscan.com/tx/",
            42161: "https://arbiscan.io/tx/",
            10: "https://optimistic.etherscan.io/tx/",
            8453: "https://basescan.org/tx/"
        }
        
        explorer_base = explorers.get(chain_id)
        if explorer_base:
            return f"{explorer_base}{tx_hash}"
        return None
    
    def _get_address_explorer_link(self, address: str, chain_id: int) -> Optional[str]:
        """Generate blockchain explorer link for address"""
        if not address or address == 'N/A' or chain_id == 31337:
            return None
            
        explorers = {
            1: "https://etherscan.io/address/",
            137: "https://polygonscan.com/address/",
            42161: "https://arbiscan.io/address/",
            10: "https://optimistic.etherscan.io/address/",
            8453: "https://basescan.org/address/"
        }
        
        explorer_base = explorers.get(chain_id)
        if explorer_base:
            return f"{explorer_base}{address}"
        return None
    
    def _format_address_with_links(self, address: str, chain_id: int, address_type: str = 'address', internal_link: str = None) -> str:
        """Format address as a single hyperlink (prefer explorer for non-local chains)."""
        if not address or address == 'N/A':
            return 'N/A'
            
        # Short address for display
        short_addr = f"{address[:6]}..{address[-4:]}"  # Use two dots per requirements
        
        # Escape special characters in the display text for markdown
        escaped_short_addr = self._escape_markdown_text(short_addr)
        
        # Prefer explorer link for public chains; use app link for local
        if chain_id != 31337:
            explorer_link = self._get_address_explorer_link(address, chain_id)
            if explorer_link:
                escaped_url = self._escape_markdown_url(explorer_link)
                return f"[{escaped_short_addr}]({escaped_url})"
        # Fallback to internal app link if provided
        if internal_link:
            escaped_url = self._escape_markdown_url(internal_link)
            return f"[{escaped_short_addr}]({escaped_url})"
        # Last resort: plain short address
        return escaped_short_addr
    
    def _escape_markdown_text(self, text: str) -> str:
        """Escape minimal characters for classic Telegram Markdown (not V2)."""
        # For classic Markdown, only '_', '*', and '`' need escaping in plain text.
        for char in ['_', '*', '`']:
            text = text.replace(char, f'\\{char}')
        return text
    
    def _escape_markdown_url(self, url: str) -> str:
        """Escape special characters in markdown URLs"""
        # For URLs, we need to escape parentheses and backslashes
        # But NOT other characters that are valid in URLs
        url = url.replace('\\', '\\\\')  # Escape backslashes
        url = url.replace(')', '\\)')    # Escape closing parentheses
        url = url.replace('(', '\\(')    # Escape opening parentheses
        return url
    
    def _get_app_link(self, template: str, **kwargs) -> str:
        """Generate internal application link"""
        base_url = self._get_base_url()
        
        templates = {
            'auction_details': "/auction/{address}",
            # Include chain_id segment to match UI route: /round/:chainId/:auctionAddress/:roundId
            'round_details': "/round/{chain_id}/{auction_address}/{round_id}",
            'taker_details': "/taker/{address}"
        }
        
        if template in templates:
            path = templates[template].format(**kwargs)
            return f"{base_url}{path}"
        
        return base_url
    
    def _format_kick_event(self, event: Dict) -> str:
        """Format kick event for Telegram with proper formatting"""
        try:
            payload = json.loads(event.get('payload_json', '{}'))
            chain_id = int(event.get('chain_id', 0))
            chain_name = self._get_chain_name(chain_id)
            
            round_id = event.get('round_id', 'N/A')
            auction_addr = event.get('auction_address', 'N/A')
            from_token_addr = event.get('from_token', 'N/A')
            # Try to get want token from payload or event
            want_token_addr = payload.get('want_token') or event.get('want_token', 'N/A')
            initial_available = payload.get('initial_available', 'N/A')
            kicker = payload.get('kicker', 'N/A')
            tx_hash = self._normalize_tx_hash(event.get('tx_hash', 'N/A')) or 'N/A'
            
            # Get token symbols
            from_token_info = self._get_token_info(from_token_addr, chain_id) if from_token_addr != 'N/A' else {}
            from_token_symbol = from_token_info.get('symbol', 'TOKEN')
            want_token_info = self._get_token_info(want_token_addr, chain_id) if want_token_addr and want_token_addr != 'N/A' else {}
            want_token_symbol = want_token_info.get('symbol', 'TOKEN')
            
            # Format addresses with links
            auction_internal_link = self._get_app_link('auction_details', address=auction_addr)
            auction_formatted = self._format_address_with_links(auction_addr, chain_id, 'auction', auction_internal_link)
            
            kicker_formatted = 'N/A'
            if kicker != 'N/A':
                kicker_internal_link = self._get_app_link('taker_details', address=kicker)
                kicker_formatted = self._format_address_with_links(kicker, chain_id, 'kicker', kicker_internal_link)
            
            message = f"🚀 **New Auction Round**\n\n"
            message += f"Chain: {chain_name}\n"
            # Round number hyperlinked to app round page
            try:
                round_link = self._get_app_link('round_details', chain_id=chain_id, auction_address=auction_addr, round_id=round_id)
                round_link_escaped = self._escape_markdown_url(round_link)
                message += f"Round: [#{round_id}]({round_link_escaped})\n"
            except Exception:
                message += f"Round: #{round_id}\n"
            # Auction address as hyperlink (no emoji)
            message += f"Auction: {auction_formatted}\n"
            
            if kicker_formatted != 'N/A':
                message += f"Kicker: {kicker_formatted}\n"
            
            # Token pair
            if want_token_addr and want_token_addr != 'N/A':
                message += f"Pair: {from_token_symbol} → {want_token_symbol}\n"
            else:
                message += f"Token: {from_token_symbol}\n"
            
            if initial_available != 'N/A':
                formatted_available = self._format_amount(str(initial_available))
                message += f"Available: {formatted_available} {from_token_symbol}\n"
            
            # Add transaction link
            explorer_link = self._get_explorer_link(tx_hash, chain_id)
            if explorer_link:
                chain_name_short = chain_name.split()[0]
                message += f"\n🔗 [View on Explorer]({explorer_link})"
            elif tx_hash and tx_hash != 'N/A':
                message += f"\n🔗 Transaction: {tx_hash[:8]}...{tx_hash[-6:]}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting kick event: {e}")
            return "🚀 New Auction Round! (formatting error)"
    
    def _format_take_event(self, event: Dict) -> str:
        """Format take event for Telegram with proper formatting"""
        try:
            payload = json.loads(event.get('payload_json', '{}'))
            chain_id = int(event.get('chain_id', 0))
            chain_name = self._get_chain_name(chain_id)
            
            round_id = event.get('round_id', 'N/A')
            taker = payload.get('taker', 'N/A')
            amount_taken = payload.get('amount_taken', 'N/A')
            amount_paid = payload.get('amount_paid', 'N/A')
            tx_hash = self._normalize_tx_hash(event.get('tx_hash', 'N/A')) or 'N/A'
            
            from_token_addr = event.get('from_token', 'N/A')
            want_token_addr = event.get('want_token', 'N/A')
            
            # Get token info
            from_token_info = self._get_token_info(from_token_addr, chain_id) if from_token_addr != 'N/A' else {}
            want_token_info = self._get_token_info(want_token_addr, chain_id) if want_token_addr != 'N/A' else {}
            
            from_token_symbol = from_token_info.get('symbol', 'TOKEN')
            want_token_symbol = want_token_info.get('symbol', 'TOKEN')
            
            message = f"💰 **Take**\n\n"
            
            # Taker with links
            if taker != 'N/A':
                taker_internal_link = self._get_app_link('taker_details', address=taker)
                taker_formatted = self._format_address_with_links(taker, chain_id, 'taker', taker_internal_link)
                message += f"Taker: {taker_formatted}\n"
            
            # Amount taken with token symbol
            if amount_taken != 'N/A':
                formatted_taken = self._format_amount(str(amount_taken))
                message += f"Bought: {formatted_taken} {from_token_symbol}\n"
            
            # Amount paid with token symbol  
            if amount_paid != 'N/A':
                formatted_paid = self._format_amount(str(amount_paid))
                message += f"Paid: {formatted_paid} {want_token_symbol}\n"
            
            # Chain and Round (with round link)
            auction_address = event.get('auction_address', 'N/A')
            if auction_address != 'N/A' and round_id != 'N/A':
                round_internal_link = self._get_app_link('round_details', chain_id=chain_id, auction_address=auction_address, round_id=round_id)
                round_link = f"[Round #{round_id}]({round_internal_link})"
                message += f"Chain: {chain_name} | {round_link}\n"
            else:
                message += f"Chain: {chain_name} | Round #{round_id}\n"
            
            # Transaction link
            explorer_link = self._get_explorer_link(tx_hash, chain_id)
            if explorer_link:
                escaped_explorer_link = self._escape_markdown_url(explorer_link)
                message += f"\n🔗 [View on Explorer]({escaped_explorer_link})"
            elif tx_hash and tx_hash != 'N/A':
                message += f"\n🔗 Transaction: {tx_hash[:8]}...{tx_hash[-6:]}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting take event: {e}")
            return "💰 Auction Take! (formatting error)"
    
    def _format_deploy_event(self, event: Dict) -> str:
        """Format deploy event for Telegram with proper formatting"""
        try:
            payload = json.loads(event.get('payload_json', '{}'))
            chain_id = int(event.get('chain_id', 0))
            chain_name = self._get_chain_name(chain_id)
            
            auction_addr = event.get('auction_address', 'N/A')
            version = payload.get('version', 'N/A')
            want_token_addr = payload.get('want_token', 'N/A')
            starting_price = payload.get('starting_price', 'N/A')
            decay_rate = payload.get('decay_rate', 'N/A')
            governance_addr = payload.get('governance', 'N/A')
            tx_hash = event.get('tx_hash', 'N/A')
            
            # Get want token info
            want_token_info = self._get_token_info(want_token_addr, chain_id) if want_token_addr != 'N/A' else {}
            want_token_symbol = want_token_info.get('symbol', 'TOKEN')
            
            message = f"🏭 **New Auction Deployed**\n\n"
            message += f"Chain: {chain_name}\n"
            
            # Auction address with internal link and explorer link
            if auction_addr != 'N/A':
                auction_internal_link = self._get_app_link('auction_details', address=auction_addr)
                auction_formatted = self._format_address_with_links(auction_addr, chain_id, 'auction', auction_internal_link)
                message += f"Address: {auction_formatted}\n"
                
            message += f"Want Token: {want_token_symbol}\n"
            message += f"Version: {version}\n"
            
            # Add governance address with link
            if governance_addr != 'N/A':
                governance_explorer_link = self._get_address_explorer_link(governance_addr, chain_id)
                if governance_explorer_link and chain_id != 31337:
                    governance_formatted = f"[{governance_addr[:6]}...{governance_addr[-4:]}]({governance_explorer_link})"
                else:
                    governance_formatted = f"{governance_addr[:6]}...{governance_addr[-4:]}"
                message += f"Governance: {governance_formatted}\n"
            
            if starting_price != 'N/A':
                formatted_price = self._format_amount(str(starting_price))
                message += f"Starting Price: {formatted_price} {want_token_symbol}\n"
                
            if decay_rate != 'N/A':
                try:
                    rate_pct = float(decay_rate) * 100
                    message += f"Decay Rate: {rate_pct:.2f}% per hour\n"
                except (ValueError, TypeError):
                    pass
            
            # Transaction link
            explorer_link = self._get_explorer_link(tx_hash, chain_id)
            if explorer_link:
                chain_name_short = chain_name.split()[0]
                message += f"\n🔗 [View on Explorer]({explorer_link})"
            elif tx_hash and tx_hash != 'N/A':
                message += f"\n🔗 Transaction: {tx_hash[:8]}...{tx_hash[-6:]}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting deploy event: {e}")
            return "🏭 New Auction Deployed! (formatting error)"
    
    async def run(self):
        """Main consumer loop"""
        logger.info(f"🚀 Starting Telegram Consumer as {self.consumer_name}")
        if self.bot and self.active_groups:
            logger.info(f"📊 Active groups: {len(self.active_groups)}")
            for group_name, group_data in self.active_groups.items():
                logger.info(f"   • {group_name}: {group_data['chat_id']} ({group_data['config'].get('description', 'No description')})")
        else:
            logger.info("📱 Running in TEST MODE - messages will be logged only")
        logger.info(f"📡 Consuming from Redis stream: {self.stream_key}")
        
        while True:
            try:
                # Read with consumer group
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: '>'},
                    count=10,
                    block=5000  # Block for 5 seconds
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, data in stream_messages:
                        # Process event
                        success = await self.process_event(data)
                        
                        if success:
                            # Acknowledge successful processing
                            self.redis_client.xack(
                                self.stream_key,
                                self.consumer_group,
                                message_id
                            )
                        else:
                            # Log but still acknowledge to prevent blocking
                            logger.warning(f"Processing failed for {message_id}, acknowledging anyway")
                            self.redis_client.xack(
                                self.stream_key,
                                self.consumer_group,
                                message_id
                            )
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping consumer...")
                break
            except redis.exceptions.TimeoutError:
                # Normal when no new messages within block timeout
                continue
            except Exception as e:
                logger.warning(f"Consumer warning: {e}")
                await asyncio.sleep(0.5)

async def main():
    # Load environment variables
    load_dotenv()
    
    env_url = os.getenv('REDIS_URL')
    redis_url = env_url if (env_url and env_url.strip()) else None
    consumer = TelegramConsumer(redis_url)
    await consumer.run()

if __name__ == '__main__':
    # Show startup info
    load_dotenv()
    
    # Debug environment variables
    logger.info("Environment variables check:")
    logger.info(f"  TELEGRAM_BOT_TOKEN: {'✅ Set' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ Not set'}")
    logger.info(f"  TELEGRAM_CHAT_ID: {'✅ Set' if os.getenv('TELEGRAM_CHAT_ID') else '❌ Not set'}")
    logger.info(f"  TELEGRAM_GROUP_1_ID: {'✅ Set' if os.getenv('TELEGRAM_GROUP_1_ID') else '❌ Not set'}")
    
    asyncio.run(main())
