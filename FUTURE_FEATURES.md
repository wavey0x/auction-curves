# Future Features - Redis Integration & Performance Enhancements

## Overview

This document outlines future performance and real-time features for the Auction System. These features should be implemented when user scale grows beyond 10-50 concurrent users or when sub-second updates become critical.

**Current Status**: Not needed at current scale (1-10 users). PostgreSQL is sufficient.

**Implementation Trigger**: Consider when you hit:
- 50+ concurrent users
- API response times >500ms consistently
- Need for sub-second auction updates
- Database CPU usage >50%

---

## 1. Redis Streams with Rindexer (Native Support)

### Overview
Rindexer has **native Redis streams support** which allows publishing blockchain events directly to Redis for multiple consumers to process in real-time.

**Documentation**: https://rindexer.xyz/docs/start-building/streams/redis

### Current Architecture
```
Blockchain → Rindexer → PostgreSQL only
                ↓
            API polls database
```

### Future Architecture with Redis Streams
```
Blockchain → Rindexer → PostgreSQL (persistence)
                ↓
              Redis Streams (real-time)
                ↓
         Multiple consumers:
         - API server (cache invalidation)
         - Analytics service (metrics)
         - WebSocket service (live updates)
         - Alert service (notifications)
```

### Implementation

#### 1. Update Rindexer Configuration
Add Redis streams to your existing `rindexer-local.yaml` and `rindexer-multi.yaml`:

```yaml
# indexer/rindexer/rindexer-redis.yaml
name: "auction_system_redis"
description: "Auction system with Redis streams"

networks:
  - name: ethereum
    chain_id: 1
    rpc: ${ETHEREUM_RPC_URL}
    compute_units_per_second: 330

contracts:
  - name: AuctionFactory
    address: ${FACTORY_ADDRESS}
    abi: "./abis/AuctionFactory.json"
    include_events:
      - DeployedNewAuction
    network: ethereum
    
  - name: Auction
    address: # Dynamic addresses from factory
    abi: "./abis/Auction.json" 
    include_events:
      - AuctionRoundKicked
      - AuctionSale
    network: ethereum

# Add Redis streams configuration
streams:
  redis:
    connection_uri: ${REDIS_CONNECTION_URI}
    streams:
      # High-value sales stream (for alerts)
      - stream_name: "auction_high_value_sales"
        networks: [ethereum]
        events:
          - event_name: AuctionSale
            alias: "high_value_sale"
            conditions:
              - "amount_paid": ">=1000000000000000000"  # >= 1 ETH
      
      # All kicks stream (for real-time updates)
      - stream_name: "auction_kicks"
        networks: [ethereum] 
        events:
          - event_name: AuctionRoundKicked
            alias: "round_kicked"
      
      # All sales stream (for activity feed)
      - stream_name: "auction_sales"
        networks: [ethereum]
        events:
          - event_name: AuctionSale
            alias: "sale_completed"

# Keep existing storage for persistence
storage:
  postgres:
    enabled: true
    drop_each_run: false
    connection_uri: ${DATABASE_URL}
```

#### 2. Environment Configuration
Add Redis connection to your unified `.env`:

```bash
# Add to .env file - Redis Configuration
REDIS_CONNECTION_URI=redis://localhost:6379

# Mode-specific Redis configs
DEV_REDIS_CONNECTION_URI=redis://localhost:6379
PROD_REDIS_CONNECTION_URI=redis://user:pass@prod-redis:6379/0
MOCK_REDIS_CONNECTION_URI=  # Mock mode doesn't need Redis
```

#### 3. Docker Compose Addition
```yaml
# Add to docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 3s
      retries: 3

volumes:
  redis_data:
```

---

## 2. API Response Caching Layer

### Implementation Strategy

#### 1. Redis Cache Client
```python
# monitoring/api/cache.py
import redis
import json
from typing import Optional, Any
from functools import wraps
import hashlib

class AuctionCache:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            health_check_interval=30
        )
    
    def cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache keys"""
        key_data = f"{prefix}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data"""
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, data: Any, ttl: int = 30):
        """Cache data with TTL"""
        self.client.setex(key, ttl, json.dumps(data, default=str))
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)

cache = AuctionCache()
```

#### 2. Cache Decorators
```python
# monitoring/api/decorators.py
def cache_response(ttl: int = 30, key_prefix: str = "api"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = cache.cache_key(key_prefix, func.__name__, *args, **kwargs)
            
            # Try cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Cache miss - call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

#### 3. Cached API Endpoints
```python
# monitoring/api/app.py - Updated endpoints
from .cache import cache
from .decorators import cache_response

@app.get("/auctions")
@cache_response(ttl=30, key_prefix="auctions_list")
async def get_auctions(
    status: str = "all",
    chain_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20
):
    # Original database query
    # Result will be cached for 30 seconds
    pass

@app.get("/auctions/{address}")
@cache_response(ttl=10, key_prefix="auction_details")
async def get_auction_details(address: str):
    # Auction details cached for 10 seconds
    pass

@app.get("/auctions/{address}/price-history")
@cache_response(ttl=60, key_prefix="price_history") 
async def get_price_history(address: str, hours: int = 24):
    # Price history cached for 1 minute
    pass
```

#### 4. Cache Invalidation via Redis Streams
```python
# monitoring/api/stream_consumer.py
import asyncio
import redis.asyncio as redis

class CacheInvalidator:
    def __init__(self):
        self.redis = redis.Redis.from_url(os.getenv('REDIS_CONNECTION_URI'))
    
    async def listen_for_events(self):
        """Listen to Rindexer events and invalidate cache"""
        while True:
            try:
                # Read from multiple streams
                streams = {
                    "auction_sales": "$",
                    "auction_kicks": "$"
                }
                
                messages = await self.redis.xread(streams, block=1000)
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        await self.handle_event(stream.decode(), fields)
                        
            except Exception as e:
                print(f"Stream error: {e}")
                await asyncio.sleep(1)
    
    async def handle_event(self, stream: str, event_data: dict):
        """Invalidate relevant caches based on events"""
        if stream == "auction_sales":
            auction_address = event_data.get(b'auction', b'').decode()
            if auction_address:
                # Invalidate auction-specific caches
                cache.invalidate_pattern(f"auction_details:*{auction_address}*")
                cache.invalidate_pattern(f"price_history:*{auction_address}*")
                # Invalidate general lists
                cache.invalidate_pattern("auctions_list:*")
        
        elif stream == "auction_kicks":
            auction_address = event_data.get(b'auction', b'').decode()
            if auction_address:
                # New round started - invalidate auction details
                cache.invalidate_pattern(f"auction_details:*{auction_address}*")
                cache.invalidate_pattern("auctions_list:*")

# Start as background task in FastAPI
@app.on_event("startup")
async def start_cache_invalidator():
    invalidator = CacheInvalidator()
    asyncio.create_task(invalidator.listen_for_events())
```

---

## 3. Real-time Features Implementation

### 3.1 Server-Sent Events (SSE) for Live Updates

#### API Endpoint
```python
# monitoring/api/app.py
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

@app.get("/events/auction/{auction_address}")
async def auction_events(auction_address: str):
    """Server-sent events for real-time auction updates"""
    
    async def event_generator():
        redis_client = redis.Redis.from_url(os.getenv('REDIS_CONNECTION_URI'))
        
        # Subscribe to auction-specific events
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"auction:{auction_address}")
        
        try:
            while True:
                message = await pubsub.get_message(timeout=30)
                if message and message['type'] == 'message':
                    yield {
                        "event": "auction_update",
                        "data": message['data'].decode()
                    }
        finally:
            await pubsub.unsubscribe(f"auction:{auction_address}")
            await pubsub.close()
    
    return EventSourceResponse(event_generator())
```

#### Frontend Integration
```typescript
// ui/src/hooks/useRealtimeAuction.ts
import { useEffect, useState } from 'react'

interface AuctionUpdate {
  type: 'sale' | 'kick' | 'price_update'
  data: any
}

export function useRealtimeAuction(auctionAddress: string) {
  const [updates, setUpdates] = useState<AuctionUpdate[]>([])
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/events/auction/${auctionAddress}`
    )
    
    eventSource.onmessage = (event) => {
      const update: AuctionUpdate = JSON.parse(event.data)
      setUpdates(prev => [update, ...prev.slice(0, 49)]) // Keep last 50
    }
    
    eventSource.onerror = () => {
      console.log('SSE connection lost, retrying...')
    }
    
    return () => eventSource.close()
  }, [auctionAddress])
  
  return updates
}
```

### 3.2 Activity Feed Optimization

#### Redis List-based Activity Feed
```python
# monitoring/api/activity_feed.py
class ActivityFeedManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(os.getenv('REDIS_CONNECTION_URI'))
        self.MAX_ACTIVITIES = 1000
    
    async def add_activity(self, activity: dict):
        """Add new activity to feed"""
        activity_json = json.dumps(activity, default=str)
        
        # Add to global feed
        await self.redis.lpush("activity:global", activity_json)
        await self.redis.ltrim("activity:global", 0, self.MAX_ACTIVITIES - 1)
        
        # Add to auction-specific feed
        auction_address = activity.get('auction_address')
        if auction_address:
            await self.redis.lpush(f"activity:auction:{auction_address}", activity_json)
            await self.redis.ltrim(f"activity:auction:{auction_address}", 0, 99)
        
        # Publish for real-time updates
        await self.redis.publish("activity:new", activity_json)
    
    async def get_recent_activity(self, limit: int = 20, auction_address: str = None):
        """Get recent activity from cache"""
        key = f"activity:auction:{auction_address}" if auction_address else "activity:global"
        
        activities = await self.redis.lrange(key, 0, limit - 1)
        return [json.loads(activity) for activity in activities]

# Integrate with stream consumer
async def handle_sale_event(event_data: dict):
    activity = {
        "type": "sale",
        "auction_address": event_data['auction'],
        "amount": event_data['amount_paid'],
        "price": event_data['price'],
        "timestamp": event_data['timestamp'],
        "tx_hash": event_data['tx_hash']
    }
    
    feed_manager = ActivityFeedManager()
    await feed_manager.add_activity(activity)
```

---

## 4. Performance Monitoring & Metrics

### 4.1 Cache Hit Rate Monitoring
```python
# monitoring/api/metrics.py
import time
from typing import Dict

class PerformanceMetrics:
    def __init__(self):
        self.redis = redis.Redis.from_url(os.getenv('REDIS_CONNECTION_URI'))
        self.start_time = time.time()
    
    async def record_cache_hit(self, cache_type: str):
        """Record cache hit"""
        await self.redis.incr(f"metrics:cache_hits:{cache_type}")
        await self.redis.incr("metrics:cache_hits:total")
    
    async def record_cache_miss(self, cache_type: str):
        """Record cache miss"""
        await self.redis.incr(f"metrics:cache_misses:{cache_type}")
        await self.redis.incr("metrics:cache_misses:total")
    
    async def get_cache_stats(self) -> Dict[str, float]:
        """Get cache performance statistics"""
        hits = int(await self.redis.get("metrics:cache_hits:total") or 0)
        misses = int(await self.redis.get("metrics:cache_misses:total") or 0)
        total = hits + misses
        
        return {
            "cache_hit_rate": hits / total if total > 0 else 0,
            "total_requests": total,
            "cache_hits": hits,
            "cache_misses": misses
        }

@app.get("/metrics")
async def get_system_metrics():
    """System performance metrics endpoint"""
    metrics = PerformanceMetrics()
    return await metrics.get_cache_stats()
```

---

## 5. Implementation Roadmap

### Phase 1: Basic Caching (Immediate Impact)
**Triggers**: 20+ concurrent users OR response times >300ms

1. Add Redis container to docker-compose.yml
2. Implement basic response caching for:
   - `/auctions` endpoint (30s TTL)
   - `/auctions/{address}` endpoint (10s TTL)
   - Price history queries (60s TTL)

**Expected Impact**: 5-10x faster responses for cached data

### Phase 2: Rindexer Streams Integration
**Triggers**: Need for real-time updates OR 50+ concurrent users

1. Update rindexer configuration with Redis streams
2. Implement cache invalidation via stream events
3. Add activity feed using Redis lists
4. Performance monitoring and metrics

**Expected Impact**: Real-time updates, intelligent cache invalidation

### Phase 3: Advanced Real-time Features  
**Triggers**: 100+ concurrent users OR competitive auction requirements

1. Server-Sent Events for live updates
2. WebSocket fallback for older browsers
3. Advanced filtering and personalization
4. Push notifications for high-value events

**Expected Impact**: Sub-second updates, enhanced user experience

### Phase 4: Scaling & Optimization
**Triggers**: 500+ concurrent users OR multi-region deployment

1. Redis Cluster for high availability
2. Geographic distribution
3. Advanced caching strategies
4. Rate limiting and DDoS protection

---

## 6. Testing & Validation

### Load Testing Commands
```bash
# Test current system performance
ab -n 1000 -c 10 http://localhost:8000/auctions

# Test with Redis caching
ab -n 1000 -c 10 http://localhost:8000/auctions
# Should show dramatically improved response times

# Test cache invalidation
curl -X POST http://localhost:8000/test/invalidate-cache
ab -n 100 -c 5 http://localhost:8000/auctions
```

### Monitoring Commands
```bash
# Monitor Redis streams
redis-cli XREAD STREAMS auction_sales auction_kicks $ $

# Monitor cache hit rates  
curl http://localhost:8000/metrics | jq '.cache_hit_rate'

# Monitor Redis memory usage
redis-cli INFO memory
```

---

## 7. Configuration Management

### Environment Variables to Add
```bash
# Redis Configuration
REDIS_CONNECTION_URI=redis://localhost:6379
REDIS_MAX_CONNECTIONS=50
REDIS_TIMEOUT=5

# Cache Configuration  
CACHE_DEFAULT_TTL=30
CACHE_LONG_TTL=300
CACHE_SHORT_TTL=10

# Stream Configuration
ENABLE_REDIS_STREAMS=true
STREAM_CONSUMER_GROUP=auction_api
```

### Update run.sh Script
```bash
# Add Redis health check to run.sh
check_redis() {
    if [ "$MODE" != "mock" ]; then
        if ! redis-cli ping >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️ Redis not running. Starting Redis container...${NC}"
            docker-compose up -d redis
            sleep 3
        fi
    fi
}
```

---

## 8. Migration Strategy

### Step 1: Add Redis Without Breaking Changes
- Redis is optional - system works without it
- Gradual rollout: enable caching for specific endpoints first
- Monitor performance improvements

### Step 2: Enable Stream Processing  
- Configure Rindexer streams alongside existing PostgreSQL storage
- Implement cache invalidation listeners
- Test real-time features

### Step 3: Optimize Based on Usage
- Monitor cache hit rates and adjust TTL values
- Identify high-traffic endpoints for optimization
- Scale Redis infrastructure as needed

---

## Notes for LLM Implementation

1. **Start Small**: Implement basic response caching first - biggest impact with minimal complexity
2. **Test Incrementally**: Each phase should be tested thoroughly before moving to the next
3. **Monitor Performance**: Always measure before/after performance to validate improvements
4. **Graceful Degradation**: System should work even if Redis is unavailable
5. **Security**: Use Redis AUTH in production, secure connection strings
6. **Documentation**: Update API docs to reflect caching behavior and real-time endpoints

**Remember**: Only implement these features when you have a real performance problem. The current PostgreSQL-only architecture is perfectly suitable for the current scale.

---

**Implementation Checklist**:
- [ ] Add Redis to docker-compose.yml
- [ ] Create cache client wrapper 
- [ ] Implement response caching decorators
- [ ] Update rindexer.yaml with streams
- [ ] Create stream event consumers
- [ ] Implement cache invalidation logic
- [ ] Add performance metrics
- [ ] Create SSE endpoints for real-time updates
- [ ] Update frontend for real-time features
- [ ] Load test and optimize TTL values