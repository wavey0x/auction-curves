"""
Event publishing helper for the indexer.
Inserts events into the outbox table within the same transaction.
"""
import json
from typing import Dict, Any, Optional
from decimal import Decimal

class EventPublisher:
    """Helper class to publish events to the outbox table"""
    
    EVENT_TYPES = {
        'AUCTION_DEPLOYED': 'deploy',
        'ROUND_KICKED': 'kick', 
        'TAKE_EXECUTED': 'take',
    }
    
    @staticmethod
    def create_uniq_key(chain_id: int, tx_hash: str, log_index: int) -> str:
        """Create unique idempotency key for an event"""
        # Normalize to ensure consistent idempotency regardless of caller formatting
        txs = EventPublisher.normalize_tx_hash(tx_hash)
        # Use lower-case without 0x in uniq to stay stable across historical differences
        txs_noprefix = txs[2:] if isinstance(txs, str) and txs.startswith('0x') else txs
        return f"{chain_id}:{txs_noprefix.lower()}:{log_index}"
    
    @staticmethod
    def decimal_to_str(obj):
        """Convert Decimal to string for JSON serialization"""
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError

    @staticmethod
    def normalize_tx_hash(tx_hash: Any) -> str:
        """Normalize transaction hash to a hex string with 0x prefix.

        Accepts bytes/bytearray/HexBytes or str. Does not alter case of provided str
        beyond ensuring the 0x prefix exists.
        """
        try:
            # Bytes-like (including HexBytes)
            if isinstance(tx_hash, (bytes, bytearray)):
                return '0x' + tx_hash.hex()
            # Some web3 HexBytes also support .hex() method returning '0x...'
            hx = getattr(tx_hash, 'hex', None)
            if callable(hx):
                s = hx()
                if isinstance(s, str):
                    return s if s.startswith('0x') else f'0x{s}'
            s = str(tx_hash)
            return s if s.startswith('0x') else f'0x{s}'
        except Exception:
            s = str(tx_hash)
            return s if s.startswith('0x') else f'0x{s}'
    
    def insert_outbox_event(
        self,
        cursor,
        event_type: str,
        chain_id: int,
        block_number: int,
        tx_hash: str,
        log_index: int,
        auction_address: str,
        timestamp: int,
        payload: Dict[str, Any],
        round_id: Optional[int] = None,
        from_token: Optional[str] = None,
        want_token: Optional[str] = None
    ) -> None:
        """
        Insert event into outbox table.
        Should be called within the same transaction as domain inserts.
        """
        # Normalize tx hash consistently
        tx_hash_norm = self.normalize_tx_hash(tx_hash)
        uniq = self.create_uniq_key(chain_id, tx_hash_norm, log_index)
        
        # Ensure payload is JSON-serializable
        payload_json = json.dumps(payload, default=self.decimal_to_str)
        
        cursor.execute("""
            INSERT INTO outbox_events (
                type, chain_id, block_number, tx_hash, log_index,
                auction_address, round_id, from_token, want_token,
                timestamp, payload_json, uniq, ver
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            ON CONFLICT (uniq) DO NOTHING
        """, (
            event_type, chain_id, block_number, tx_hash_norm, log_index,
            auction_address, round_id, from_token, want_token,
            timestamp, payload_json, uniq
        ))
