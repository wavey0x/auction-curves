from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Dict, Any, List
import os
import asyncio
import aiohttp
import json

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None

# Import using absolute module name because app runs as a script from this folder
from database import get_db

router = APIRouter()


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _status_from_age(age_sec: int, ok: int, warn: int) -> str:
    if age_sec <= ok:
        return "ok"
    if age_sec <= warn:
        return "degraded"
    return "down"


async def _get_chain_head_block() -> int | None:
    """Get current chain head block number via RPC."""
    rpc_url = os.getenv("DEV_ANVIL_RPC_URL", "http://localhost:8545")
    if not rpc_url:
        return None
    
    try:
        timeout = aiohttp.ClientTimeout(total=3)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            async with session.post(rpc_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data:
                        # Convert hex to int
                        return int(data["result"], 16)
    except Exception:
        pass
    
    return None


def _build_redis_url_for_status() -> str | None:
    """Build a Redis URL using the same conventions as other services.

    Prefers `REDIS_URL`. Otherwise builds from parts, trying consumer/publisher creds,
    then generic username/password, then password-only.
    """
    url = os.getenv("REDIS_URL")
    if url and url.strip():
        return url.strip()

    host = (os.getenv("REDIS_HOST") or "localhost").strip()
    port = (os.getenv("REDIS_PORT") or "6379").strip()
    db = (os.getenv("REDIS_DB") or "0").strip()
    tls = (os.getenv("REDIS_TLS") or "false").strip().lower() in ("1","true","yes","on")
    scheme = "rediss" if tls else "redis"

    # Prefer consumer role for read/ping
    user = (os.getenv("REDIS_CONSUMER_USER") or os.getenv("REDIS_USERNAME") or "").strip()
    pwd = (os.getenv("REDIS_CONSUMER_PASS") or os.getenv("REDIS_PASSWORD") or "").strip()
    if not user and not pwd:
        # Try publisher as a fallback, or password-only
        user = (os.getenv("REDIS_PUBLISHER_USER") or user).strip()
        pwd = (os.getenv("REDIS_PUBLISHER_PASS") or pwd).strip()

    auth = ""
    if user and pwd:
        auth = f"{user}:{pwd}@"
    elif pwd:
        auth = f":{pwd}@"

    return f"{scheme}://{auth}{host}:{port}/{db}"


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    now = _now_epoch()

    # Thresholds (seconds)
    idx_ok = int(os.getenv("DEV_INDEXER_OK_SEC", "30"))
    idx_warn = int(os.getenv("DEV_INDEXER_WARN_SEC", "120"))
    price_ok = int(os.getenv("DEV_PRICE_OK_SEC", "600"))
    price_warn = int(os.getenv("DEV_PRICE_WARN_SEC", "1800"))
    relay_warn = int(os.getenv("DEV_RELAY_WARN", "100"))
    relay_crit = int(os.getenv("DEV_RELAY_CRIT", "1000"))

    services: List[Dict[str, Any]] = []

    # API (self)
    services.append({
        "name": "api",
        "status": "ok",
        "detail": "FastAPI responding",
        "metrics": {"time": now}
    })

    # Database health
    db_status = {
        "name": "postgres",
        "status": "unknown",
        "detail": "",
        "metrics": {}
    }
    try:
        res = await db.execute(text("SELECT 1"))
        one = res.scalar()
        ok = (one == 1)
        db_status["status"] = "ok" if ok else "down"
        db_status["detail"] = "Connected" if ok else "Query failed"
    except Exception as e:
        db_status["status"] = "down"
        db_status["detail"] = str(e)[:200]
    services.append(db_status)

    # Redis health (optional)
    redis_status = {
        "name": "redis",
        "status": "unknown",
        "detail": "",
        "metrics": {}
    }
    if not redis:
        redis_status["status"] = "unknown"
        redis_status["detail"] = "redis client not installed"
    else:
        redis_url = _build_redis_url_for_status()
        if not redis_url:
            redis_status["status"] = "unknown"
            redis_status["detail"] = "No Redis configuration found"
        else:
            try:
                client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                pong = client.ping()
                redis_status["status"] = "ok" if pong else "down"
                redis_status["detail"] = "PONG" if pong else "No response"
            except Exception as e:
                # If auth may be the issue, try unauth ping by stripping credentials
                try:
                    noauth_url = redis_url
                    if "@" in noauth_url:
                        scheme = noauth_url.split("://",1)[0]
                        rest = noauth_url.split("@",1)[1]
                        noauth_url = f"{scheme}://{rest}"
                    client = redis.from_url(
                        noauth_url,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2,
                    )
                    pong = client.ping()
                    if pong:
                        redis_status["status"] = "ok"
                        redis_status["detail"] = "PONG (unauth)"
                    else:
                        redis_status["status"] = "down"
                        redis_status["detail"] = "No response"
                except Exception:
                    redis_status["status"] = "down"
                    redis_status["detail"] = str(e)[:200]
    services.append(redis_status)

    # Indexer recency and block lag
    idx_status = {
        "name": "indexer",
        "status": "unknown",
        "detail": "",
        "metrics": {}
    }
    try:
        res = await db.execute(text(
            """
            SELECT MAX(updated_at) AS updated_at, MAX(last_indexed_block) AS last_block
            FROM indexer_state
            """
        ))
        row = res.fetchone()
        if row and row[0] is not None:
            updated_at = int(row[0].timestamp()) if hasattr(row[0], 'timestamp') else int(row[0])
            age = max(0, now - updated_at)
            indexed_block = int(row[1] or 0)
            
            # Get chain head for block lag detection
            chain_head = await _get_chain_head_block()
            
            # Determine status based on age and block lag
            age_status = _status_from_age(age, idx_ok, idx_warn)
            block_lag_status = "ok"
            block_lag = 0
            
            if chain_head is not None and indexed_block > 0:
                block_lag = max(0, chain_head - indexed_block)
                if block_lag > 10:
                    block_lag_status = "degraded"
                    
            # Use worst status between age and block lag
            if age_status == "down" or block_lag_status == "down":
                final_status = "down"
            elif age_status == "degraded" or block_lag_status == "degraded":
                final_status = "degraded" 
            else:
                final_status = "ok"
            
            # Build detail message
            detail_parts = [f"updated {age}s ago"]
            if chain_head is not None:
                detail_parts.append(f"{block_lag} blocks behind")
            detail = ", ".join(detail_parts)
            
            idx_status.update({
                "status": final_status,
                "detail": detail,
                "metrics": {
                    "last_block": indexed_block, 
                    "age_sec": age,
                    "chain_head": chain_head,
                    "block_lag": block_lag
                }
            })
        else:
            idx_status.update({"status": "down", "detail": "No indexer_state rows"})
    except Exception as e:
        idx_status.update({"status": "unknown", "detail": f"{e}"[:200]})
    services.append(idx_status)

    # Pricing freshness and backlog
    price_status = {
        "name": "prices",
        "status": "unknown",
        "detail": "",
        "metrics": {}
    }
    try:
        # Latest per source
        res = await db.execute(text(
            "SELECT source, MAX(timestamp) AS ts FROM token_prices GROUP BY source"
        ))
        rows = res.fetchall()
        per_source = {}
        worst = "ok"
        for r in rows:
            src = r[0]
            ts = int(r[1] or 0)
            age = max(0, now - ts) if ts > 0 else 10**9
            st = _status_from_age(age, price_ok, price_warn)
            per_source[src] = {"age_sec": age, "status": st}
            # compute worst
            order = {"ok": 0, "degraded": 1, "down": 2}
            if order.get(st, 0) > order.get(worst, 0):
                worst = st
        # Pending backlog
        res2 = await db.execute(text(
            "SELECT COUNT(*) FROM price_requests WHERE status = 'pending'"
        ))
        pending = int(res2.scalar() or 0)
        
        # If no pending requests, prices service is healthy regardless of data age
        final_status = "ok" if pending == 0 else (worst if rows else "unknown")
        
        price_status.update({
            "status": final_status,
            "detail": f"pending: {pending}",
            "metrics": {"pending": pending, "sources": per_source}
        })
    except Exception as e:
        price_status.update({"status": "unknown", "detail": f"{e}"[:200]})
    services.append(price_status)

    # Relay/outbox
    relay_status = {
        "name": "relay",
        "status": "unknown",
        "detail": "",
        "metrics": {}
    }
    try:
        res = await db.execute(text(
            "SELECT COUNT(*) FROM outbox_events WHERE published_at IS NULL"
        ))
        backlog = int(res.scalar() or 0)
        if backlog >= relay_crit:
            st = "down"
        elif backlog >= relay_warn:
            st = "degraded"
        else:
            st = "ok"
        relay_status.update({
            "status": st,
            "detail": f"unpublished: {backlog}",
            "metrics": {"unpublished": backlog}
        })
    except Exception as e:
        relay_status.update({"status": "unknown", "detail": f"{e}"[:200]})
    services.append(relay_status)

    return {
        "generated_at": now,
        "thresholds": {
            "indexer_ok": idx_ok,
            "indexer_warn": idx_warn,
            "price_ok": price_ok,
            "price_warn": price_warn,
            "relay_warn": relay_warn,
            "relay_crit": relay_crit,
        },
        "services": services,
    }
