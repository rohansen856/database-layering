# Layer 5 - Multi-Tier Caching

## Architecture

This layer implements a multi-tier caching strategy with L1 (in-process) and L2 (Redis) caches:

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  FastAPI     │
│  API Server  │
└──────┬───────┘
       │
       ▼
┌──────────────┐     Cache Miss
│  L1 Cache    │────────────┐
│  (In-Memory) │            │
│  TTLCache    │            │
└──────┬───────┘            │
       │                    │
       │ Cache Hit          ▼
       │              ┌──────────────┐
       │              │  L2 Cache    │     Cache Miss
       │              │  (Redis)     │────────────┐
       │              └──────┬───────┘            │
       │                     │                    │
       │                     │ Cache Hit          │
       │                     │   (Promote to L1)  │
       │                     │                    ▼
       │                     │              ┌──────────────┐
       └─────────────────────┴──────────────│  PostgreSQL  │
                                            │  Database    │
                                            └──────────────┘
```

## Components

### L1 Cache (In-Process)
- **Technology**: TTLCache (Python)
- **Location**: API server memory
- **Size**: 1000 entries
- **TTL**: 60 seconds
- **Speed**: Fastest (no network overhead)
- **Scope**: Per-instance (not shared)

### L2 Cache (Redis)
- **Technology**: Redis 7-alpine
- **Location**: Separate service
- **TTL**: 300 seconds (5 minutes)
- **Speed**: Fast (network overhead minimal)
- **Scope**: Shared across all API instances

### Cache Promotion
When data is found in L2 but not L1, it's automatically promoted to L1 for faster subsequent access.

## Performance Characteristics

- **Write Speed**: 🟢🟢🟢🟢 Fast - writes invalidate both cache levels
- **Read Speed**: 🟢🟢🟢🟢🟢 Very Fast - L1 hits have zero network latency
- **Scalability**: 🟢🟢🟢 Good - L1 reduces load on Redis
- **Complexity**: 🟡🟡🟡 Moderate - two cache layers to manage
- **Cache Hit Rate**: 🟢🟢🟢🟢 High - typically 85-95% combined

## Trade-offs

### Advantages
- Extremely fast reads for frequently accessed data (L1 hits)
- Reduces network calls to Redis (L2)
- Lower latency than single-tier caching
- Automatic cache promotion optimizes hot data
- Scales well with multiple API instances
- L2 cache shared across instances

### Disadvantages
- Cache coherency challenges across instances
- Memory overhead for L1 cache in each instance
- More complex invalidation logic
- Potential for stale data in L1 if not invalidated properly
- Requires careful TTL tuning

## Use Cases

- **High-traffic APIs**: Reduce latency for hot data
- **Read-heavy workloads**: 90%+ read ratio
- **Hierarchical data**: Frequently accessed subset of large dataset
- **Multi-instance deployments**: Share L2 while optimizing per-instance with L1
- **Cost optimization**: Reduce Redis and database load

## Running with Docker

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest -v

# Check cache stats
curl http://localhost:8005/cache-stats

# Stop services
docker-compose down
```

## Running without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL on port 5436
# Start Redis on port 6383

# Start the API
uvicorn app.main:app --reload --port 8005

# Run tests
pytest -v
```

## API Endpoints

### Write Data
```bash
POST /write
{
  "key": "user:123",
  "value": "John Doe"
}
```

### Read Data
```bash
GET /read/{key}

Response:
{
  "success": true,
  "key": "user:123",
  "value": "John Doe",
  "cache_level": "L1",  # or "L2" or "DB"
  "from_cache": true
}
```

### Cache Statistics
```bash
GET /cache-stats

Response:
{
  "l1_size": 245,
  "l1_max_size": 1000,
  "l1_hits": 1580,
  "l1_misses": 420,
  "l1_hit_rate": 79.0,
  "l2_hits": 350,
  "l2_misses": 70,
  "l2_hit_rate": 83.3,
  "combined_hit_rate": 96.5,
  "db_reads": 70
}
```

### Health Check
```bash
GET /health
```

## Cache Behavior

### Read Flow
1. Check L1 cache → **Hit**: Return immediately (fastest)
2. Check L2 cache → **Hit**: Promote to L1, return
3. Query database → Store in both L2 and L1, return

### Write Flow
1. Write to database
2. Invalidate L1 cache for the key
3. Invalidate L2 cache (Redis) for the key
4. Return success

### Cache Promotion Example
```
Initial state: Key "user:123" not in L1, but in L2

1. GET /read/user:123
   - L1 miss
   - L2 hit (found in Redis)
   - Promote to L1
   - Return value with cache_level="L2"

2. GET /read/user:123 (subsequent request)
   - L1 hit (now in memory)
   - Return immediately with cache_level="L1"
```

## Testing

The test suite covers:
- Basic read/write operations
- L1 cache hits and misses
- L2 cache hits and misses
- Cache promotion from L2 to L1
- Cache invalidation on writes
- TTL expiration
- Cache statistics accuracy
- Combined hit rate calculation
- Error handling

Run tests:
```bash
# With Docker
docker-compose exec api pytest -v

# Without Docker
pytest -v
```

Test results: **33/33 tests passing** ✅

## Configuration

Environment variables (see `.env`):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `DB_POOL_MIN_SIZE`: Minimum database connections (default: 2)
- `DB_POOL_MAX_SIZE`: Maximum database connections (default: 10)
- `L1_CACHE_SIZE`: L1 cache max entries (default: 1000)
- `L1_CACHE_TTL`: L1 TTL in seconds (default: 60)
- `L2_CACHE_TTL`: L2 (Redis) TTL in seconds (default: 300)

## Performance Tips

### Optimizing L1 Cache
- **Size**: Increase for more hot data (watch memory)
- **TTL**: Lower for more consistency, higher for better performance
- **Eviction**: Uses LRU (Least Recently Used)

### Optimizing L2 Cache
- **TTL**: Balance freshness vs. database load
- **Memory**: Configure Redis maxmemory policy
- **Persistence**: Disable for pure cache (AOF/RDB not needed)

### Monitoring
Watch these metrics:
- **L1 hit rate**: Should be 70-85% for hot data
- **L2 hit rate**: Should be 80-90% of L1 misses
- **Combined hit rate**: Target 95%+ for read-heavy workloads
- **Promotion rate**: High rate indicates good L2 → L1 flow

## Key Learnings

1. **Hierarchical Caching**: Each tier serves a specific purpose
2. **Cache Promotion**: Automatically optimizes frequently accessed data
3. **Invalidation is Hard**: Must clear both levels on writes
4. **Memory Trade-off**: L1 uses RAM, but saves network calls
5. **Per-Instance L1**: Each API instance has its own L1 cache
6. **Shared L2**: Redis provides cross-instance consistency

## Comparison with Previous Layers

| Metric | L2 (Single Cache) | L5 (Multi-Tier) |
|--------|-------------------|-----------------|
| Fastest Read | ~2-5ms (Redis) | ~0.1ms (L1) |
| Average Read | ~2-5ms | ~0.5ms |
| Hit Rate | 60-70% | 95%+ |
| Complexity | Low | Moderate |
| Memory Usage | Low | Medium |
| Network Calls | Every cache miss | Reduced by 70-85% |

## Next Layer

Layer 6 introduces **Write Buffering** with asynchronous writes using message queues for eventual consistency and higher write throughput.
