#!/usr/bin/env python3
"""
Unified Pricing Service

Polls price_requests from Postgres and, for each pending request, queries
multiple pricing sources (ypricemagic for historical/block price; Enso and
Odos for quote-based current prices when recent enough). Writes all successful
prices into token_prices with per-source entries, and marks the request as
completed if at least one source succeeds (or failed otherwise).

Notes:
- Consumes from Postgres table price_requests (not Redis).
- Honors recency window for quote APIs via {APP_MODE}_QUOTE_API_MAX_AGE_MINUTES.
- Skips quote APIs for native ETH; YPM handles ETH.
- Uses ON CONFLICT upsert for idempotency.
"""

import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
import argparse
from typing import Optional, Tuple, Dict, Any, List
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Optional imports from existing services for reuse
try:
    from scripts.price_service_ypm import YPriceMagicService  # type: ignore
except Exception:
    YPriceMagicService = None

try:
    from scripts.price_service_enso import EnsoPriceService  # type: ignore
except Exception:
    EnsoPriceService = None

try:
    from scripts.price_service_odos import OdosPriceService  # type: ignore
except Exception:
    OdosPriceService = None


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("price_service_multi")


ETH_SENTINEL = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"


class UnifiedPricingService:
    def __init__(
        self,
        poll_interval: int = 5,
        ypm_network: str = "electro",
        once: bool = False,
        max_workers: int = 4,
        ypm_timeout: float = 20.0,
        quote_timeout: float = 5.0,
    ):
        self.poll_interval = max(1, int(poll_interval))
        self.ypm_network = ypm_network
        self.once = once
        self.max_workers = max(1, int(max_workers))
        self.ypm_timeout = float(ypm_timeout)
        self.quote_timeout = float(quote_timeout)

        # Recency window for quote APIs
        app_mode = os.getenv('APP_MODE', 'dev').lower()
        env_key = f"{app_mode.upper()}_QUOTE_API_MAX_AGE_MINUTES"
        self.quote_max_age_minutes = int(os.getenv(env_key, '10'))

        self.db_conn = self._init_db()
        self.db_conn.autocommit = True

        # Initialize source clients
        self.ypm = None
        if YPriceMagicService is not None:
            try:
                self.ypm = YPriceMagicService(network_name=self.ypm_network, poll_interval=1, once=True)
                # Replace its DB connection with ours to avoid multiple pools
                try:
                    if getattr(self.ypm, 'db_conn', None):
                        try:
                            self.ypm.db_conn.close()
                        except Exception:
                            pass
                        self.ypm.db_conn = self.db_conn
                except Exception:
                    pass
                self.ypm._init_brownie_network()
                logger.info("✅ ypricemagic initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to init ypricemagic: {e}")
                self.ypm = None

        self.enso = None
        if EnsoPriceService is not None:
            try:
                # Constructor creates a DB connection; we won't use it. That's fine.
                self.enso = EnsoPriceService(poll_interval=0, once=True)
                logger.info("✅ Enso client initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to init Enso client: {e}")
                self.enso = None

        self.odos = None
        if OdosPriceService is not None:
            try:
                self.odos = OdosPriceService(poll_interval=0, once=True)
                logger.info("✅ Odos client initialized")
            except Exception as e:
                logger.warning(f"⚠️  Failed to init Odos client: {e}")
                self.odos = None

    def _init_db(self):
        try:
            app_mode = os.getenv('APP_MODE', 'dev').lower()
            if app_mode == 'dev':
                db_url = os.getenv('DEV_DATABASE_URL', 'postgresql://postgres:password@localhost:5433/auction_dev')
            elif app_mode == 'prod':
                db_url = os.getenv('PROD_DATABASE_URL')
            else:
                raise RuntimeError(f"Unsupported APP_MODE: {app_mode}")
            if not db_url:
                raise RuntimeError("No database URL configured")
            conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info("✅ Database connection established")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)

    def _should_call_quotes(self, txn_timestamp: Optional[int]) -> bool:
        if not txn_timestamp:
            return False
        now = int(time.time())
        return (now - int(txn_timestamp)) <= self.quote_max_age_minutes * 60

    def _normalize_addr(self, addr: str) -> str:
        return addr if addr is None else addr.strip()

    def _get_pending_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chain_id, block_number, token_address,
                           request_type, auction_address, round_id, txn_timestamp,
                           COALESCE(NULLIF(price_source, ''), 'all') AS price_source
                    FROM price_requests
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (limit,)
                )
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch pending price requests: {e}")
            return []

    def _store_token_price(
        self,
        chain_id: int,
        block_number: int,
        token_address: str,
        price_usd: Decimal,
        timestamp: int,
        txn_timestamp: Optional[int],
        source: str,
    ) -> bool:
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO token_prices (
                        chain_id, block_number, token_address,
                        price_usd, timestamp, txn_timestamp, source, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (chain_id, block_number, token_address, source)
                    DO UPDATE SET
                        price_usd = EXCLUDED.price_usd,
                        timestamp = EXCLUDED.timestamp,
                        txn_timestamp = EXCLUDED.txn_timestamp,
                        created_at = NOW()
                    """,
                    (
                        chain_id,
                        block_number,
                        token_address,
                        price_usd,
                        int(timestamp),
                        int(txn_timestamp) if txn_timestamp is not None else None,
                        source,
                    ),
                )
                return True
        except Exception as e:
            logger.warning(f"Failed to store {source} price for {token_address}: {e}")
            return False

    def _mark_completed(self, request_id: int) -> None:
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE price_requests
                    SET status = 'completed', processed_at = NOW()
                    WHERE id = %s
                    """,
                    (request_id,),
                )
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as completed: {e}")

    def _mark_failed(self, request_id: int, error_message: str) -> None:
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE price_requests
                    SET status = 'failed', error_message = %s, processed_at = NOW(),
                        retry_count = retry_count + 1
                    WHERE id = %s
                    """,
                    (error_message[:500], request_id),
                )
        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as failed: {e}")

    def _fetch_from_ypm(self, token: str, block_number: int) -> Tuple[Optional[Decimal], Optional[int], Optional[str]]:
        if not self.ypm:
            return None, None, "ypricemagic unavailable"
        try:
            price, ts, err = self.ypm.fetch_token_price(token, block_number)
            if price is None:
                return None, None, err or "ypricemagic fetch failed"
            return price, ts, None
        except Exception as e:
            return None, None, f"ypricemagic exception: {e}"

    def _fetch_from_enso(self, token: str, chain_id: int) -> Tuple[Optional[Decimal], Optional[str]]:
        if not self.enso:
            return None, "Enso client unavailable"
        try:
            # EnsoPriceService exposes get_token_price_via_route(token, chain)
            price = self.enso.get_token_price_via_route(token, chain_id)  # type: ignore
            if price is None:
                return None, "Enso returned no price"
            return Decimal(str(price)), None
        except Exception as e:
            return None, f"Enso exception: {e}"

    def _fetch_from_odos(self, token: str, chain_id: int) -> Tuple[Optional[Decimal], Optional[str]]:
        if not self.odos:
            return None, "Odos client unavailable"
        try:
            price = self.odos.fetch_token_price(token, chain_id)  # type: ignore
            if price is None:
                return None, "Odos returned no price"
            return Decimal(str(price)), None
        except Exception as e:
            return None, f"Odos exception: {e}"

    def _fan_out_fetches(self, req: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Fetch from eligible sources concurrently. Returns per-source result dicts."""
        token = self._normalize_addr(req['token_address'])
        chain_id = int(req['chain_id'])
        block_number = int(req['block_number'])
        txn_ts = req.get('txn_timestamp')

        # Determine which sources to call
        requested_sources: List[str]
        price_source = (req.get('price_source') or 'all').strip().lower()
        if price_source == 'all':
            requested_sources = ['ypm', 'enso', 'odos']
        else:
            requested_sources = [s.strip() for s in price_source.split(',') if s.strip()]

        # Recency gating for quote APIs
        allow_quotes = self._should_call_quotes(txn_ts)

        # Skip quotes for native ETH
        is_eth = token.lower() == ETH_SENTINEL.lower()
        sources_to_call: List[str] = []
        for s in requested_sources:
            if s == 'ypm':
                sources_to_call.append('ypm')
            elif s in ('enso', 'odos'):
                if not is_eth and allow_quotes:
                    sources_to_call.append(s)

        results: Dict[str, Dict[str, Any]] = {}
        if not sources_to_call:
            return results

        def run_source(src: str) -> Tuple[str, Dict[str, Any]]:
            if src == 'ypm':
                price, ts, err = self._fetch_from_ypm(token, block_number)
                return src, {"price": price, "timestamp": ts, "error": err}
            elif src == 'enso':
                price, err = self._fetch_from_enso(token, chain_id)
                return src, {"price": price, "timestamp": int(time.time()), "error": err}
            elif src == 'odos':
                price, err = self._fetch_from_odos(token, chain_id)
                return src, {"price": price, "timestamp": int(time.time()), "error": err}
            else:
                return src, {"price": None, "timestamp": None, "error": f"Unknown source {src}"}

        timeouts = {
            'ypm': self.ypm_timeout,
            'enso': self.quote_timeout,
            'odos': self.quote_timeout,
        }

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(sources_to_call))) as ex:
            future_map = {}
            for src in sources_to_call:
                future = ex.submit(run_source, src)
                future_map[future] = (src, timeouts.get(src, 5.0))

            for future in as_completed(future_map.keys()):
                src, _ = future_map[future]
                try:
                    s, payload = future.result(timeout=timeouts.get(src, 5.0))
                    results[s] = payload
                except Exception as e:
                    results[src] = {"price": None, "timestamp": None, "error": f"timeout/error: {e}"}

        return results

    def _auto_store_eth_price(self, chain_id: int, block_number: int, txn_timestamp: Optional[int]) -> None:
        """If YPM is available, store ETH block price for the same block."""
        if not self.ypm:
            return
        try:
            price, ts, err = self._fetch_from_ypm(ETH_SENTINEL, block_number)
            if price is not None and ts is not None:
                stored = self._store_token_price(chain_id, block_number, ETH_SENTINEL, price, ts, txn_timestamp, 'ypricemagic')
                if stored:
                    logger.debug(f"Auto-stored ETH price for block {block_number}: ${price}")
        except Exception:
            pass

    def process_request(self, req: Dict[str, Any]) -> None:
        request_id = req['id']
        chain_id = int(req['chain_id'])
        block_number = int(req['block_number'])
        token = self._normalize_addr(req['token_address'])
        txn_ts = req.get('txn_timestamp')

        # Fetch from sources
        results = self._fan_out_fetches(req)
        successes = 0

        for src, data in results.items():
            price = data.get('price')
            ts = data.get('timestamp')
            err = data.get('error')
            if price is not None and ts is not None:
                if self._store_token_price(chain_id, block_number, token, Decimal(str(price)), int(ts), txn_ts, 'ypricemagic' if src == 'ypm' else src):
                    successes += 1
                    logger.info(f"[{request_id}] Stored {src} price for {token[:6]}..{token[-4:]} = ${price}")
            else:
                if err:
                    logger.debug(f"[{request_id}] {src} failed: {err}")

        # Also ensure ETH pricing for this block via YPM (optional)
        try:
            self._auto_store_eth_price(chain_id, block_number, txn_ts)
        except Exception:
            pass

        if successes > 0:
            self._mark_completed(request_id)
        else:
            self._mark_failed(request_id, "No sources returned a price")

    def run(self) -> None:
        logger.info("🚀 Starting Unified Pricing Service (DB-driven)")
        logger.info(f"📊 Settings: poll={self.poll_interval}s, quotes_max_age={self.quote_max_age_minutes}m, workers={self.max_workers}")

        try:
            while True:
                pending = self._get_pending_requests()
                if not pending:
                    logger.debug("No pending price requests")
                for req in pending:
                    try:
                        self.process_request(req)
                    except Exception as e:
                        logger.error(f"Failed processing request {req.get('id')}: {e}")

                if self.once:
                    logger.info("--once complete; exiting")
                    break

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping Unified Pricing Service")
        except Exception as e:
            logger.error(f"Service error: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Unified Pricing Service (multi-source)')
    parser.add_argument('--poll-interval', type=int, default=5, help='Poll interval (seconds) when idle')
    parser.add_argument('--network', default='electro', help='Brownie network name for ypricemagic')
    parser.add_argument('--once', action='store_true', help='Process one batch then exit')
    parser.add_argument('--workers', type=int, default=4, help='Max concurrent source fetches')
    parser.add_argument('--ypm-timeout', type=float, default=20.0, help='Timeout for ypricemagic fetch (seconds)')
    parser.add_argument('--quote-timeout', type=float, default=5.0, help='Timeout for quote API fetch (seconds)')
    args = parser.parse_args()

    service = UnifiedPricingService(
        poll_interval=args.poll_interval,
        ypm_network=args.network,
        once=args.once,
        max_workers=args.workers,
        ypm_timeout=args.ypm_timeout,
        quote_timeout=args.quote_timeout,
    )
    service.run()


if __name__ == '__main__':
    main()

