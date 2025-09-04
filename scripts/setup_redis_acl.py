#!/usr/bin/env python3
"""
Setup Redis ACL users for publisher/consumer with minimal permissions.

Env:
- REDIS_URL or REDIS_HOST/PORT/DB and optional admin credentials (if required)
- REDIS_STREAM_KEY (default: events)
- REDIS_PUBLISHER_USER (default: publisher)
- REDIS_PUBLISHER_PASS (required)
- REDIS_CONSUMER_USER (default: consumer)
- REDIS_CONSUMER_PASS (required)

NOTE: For true lock-down, disable the default user: ACL SETUSER default off
      Only do this if all your clients use REDIS_URL with proper credentials.
"""

import os
import sys

def main():
    try:
        import redis
    except Exception:
        print("redis-py not installed. Run: pip install redis[hiredis]")
        sys.exit(1)

    # Build admin URL (can reuse REDIS_URL)
    url = os.getenv('REDIS_URL')
    if not url:
        host = os.getenv('REDIS_HOST', 'localhost')
        port = os.getenv('REDIS_PORT', '6379')
        db = os.getenv('REDIS_DB', '0')
        pwd = os.getenv('REDIS_ADMIN_PASS', '')
        auth = f":{pwd}@" if pwd else ""
        url = f"redis://{auth}{host}:{port}/{db}"

    stream = os.getenv('REDIS_STREAM_KEY', 'events')
    pub_user = os.getenv('REDIS_PUBLISHER_USER', 'publisher')
    pub_pass = os.getenv('REDIS_PUBLISHER_PASS')
    con_user = os.getenv('REDIS_CONSUMER_USER', 'consumer')
    con_pass = os.getenv('REDIS_CONSUMER_PASS')

    if not pub_pass or not con_pass:
        print("Missing REDIS_PUBLISHER_PASS or REDIS_CONSUMER_PASS")
        sys.exit(1)

    r = redis.from_url(url, decode_responses=True)
    try:
        r.ping()
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    # Key patterns (stream and its internal keys)
    patterns = [stream, f"{stream}:*"]
    pat = " ".join(f"~{p}" for p in patterns)

    # Publisher permissions: xadd, xinfo, xtrim, ping, auth
    pub_cmds = "+xadd +xinfo +xtrim +ping +auth"
    # Consumer permissions: xreadgroup, xread, xack, xgroup, xinfo, ping, auth
    con_cmds = "+xreadgroup +xread +xack +xgroup +xinfo +ping +auth"

    def set_user(user, passwd, cmds):
        # Create or update user with only the required commands and key patterns
        cmd = f"ACL SETUSER {user} on >{passwd} {pat} {cmds}"
        return r.execute_command(cmd)

    try:
        set_user(pub_user, pub_pass, pub_cmds)
        print(f"✅ Configured publisher user '{pub_user}'")
        set_user(con_user, con_pass, con_cmds)
        print(f"✅ Configured consumer user '{con_user}'")
    except Exception as e:
        print(f"Failed to set ACL users: {e}")
        sys.exit(1)

    # Optional: disable default user for stricter security
    if os.getenv('REDIS_DISABLE_DEFAULT_USER', 'false').lower() in ('1','true','yes','on'):
        try:
            r.execute_command("ACL SETUSER default off")
            print("🔒 Disabled default Redis user")
        except Exception as e:
            print(f"Warning: failed to disable default user: {e}")

    print("✅ Redis ACL setup complete")

if __name__ == '__main__':
    main()

