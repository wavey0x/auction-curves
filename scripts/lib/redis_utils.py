#!/usr/bin/env python3
"""
Redis connection helpers with flexible auth.

Usage:
- Prefer REDIS_URL if set (supports redis://[username:password]@host:port/db?ssl=true)
- Otherwise, build from parts:
  REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_USERNAME, REDIS_PASSWORD, REDIS_TLS
"""

import os
from typing import Optional


def build_redis_url(
    default_url: str = "redis://localhost:6379",
    role: str | None = None,
) -> str:
    # If full URL provided, respect it
    url = os.getenv("REDIS_URL")
    if url and url.strip():
        return url.strip()

    # If role-specific creds are provided, prefer them
    user = os.getenv("REDIS_USERNAME", "").strip()
    pwd = os.getenv("REDIS_PASSWORD", "").strip()
    if role == "publisher":
        user = (os.getenv("REDIS_PUBLISHER_USER") or user).strip()
        pwd = (os.getenv("REDIS_PUBLISHER_PASS") or pwd).strip()
    elif role == "consumer":
        user = (os.getenv("REDIS_CONSUMER_USER") or user).strip()
        pwd = (os.getenv("REDIS_CONSUMER_PASS") or pwd).strip()

    host = os.getenv("REDIS_HOST", "localhost").strip()
    port = os.getenv("REDIS_PORT", "6379").strip()
    db = os.getenv("REDIS_DB", "0").strip()
    tls = (os.getenv("REDIS_TLS") or "false").strip().lower() in ("1", "true", "yes", "on")

    scheme = "rediss" if tls else "redis"

    auth = ""
    if user and pwd:
        auth = f"{user}:{pwd}@"
    elif pwd:
        # Password only auth
        auth = f":{pwd}@"

    return f"{scheme}://{auth}{host}:{port}/{db}"


def get_redis_client(decode_responses: bool = True, role: str | None = None):
    import redis

    url = build_redis_url(role=role)
    # Short, sane timeouts to avoid hanging checks
    return redis.from_url(
        url,
        decode_responses=decode_responses,
        socket_connect_timeout=3,
        socket_timeout=5,
    )
