# Layer 4 - DB Sharding + Cache

This layer implements horizontal database sharding with hash-based routing and Redis caching for scalable reads and writes.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────┐
│      FastAPI Application                │
│  ┌──────────┐          ┌───────────┐    │
│  │  Write   │          │   Read    │    │
│  │ Endpoint │          │ Endpoint  │    │
│  └────┬─────┘          └─────┬─────┘    │
│       │                      │           │
│       v                      v           │
│  ┌──────────────────────────────────┐   │
│  │      Shard Router                │   │
│  │   (Hash-based key→shard map)     │   │
│  └───┬────────┬────────┬────────────┘   │
│      │        │        │      │          │
│      │        │        │      v          │
│      │        │        │  ┌────────────┐ │
│      │        │        │  │   Redis    │ │
│      │        │        │  │   Cache    │ │
│      │        │        │  └────────────┘ │
│      v        v        v                 │
│  ┌──────┐ ┌──────┐ ┌──────┐             │
│  │Shard │ │Shard │ │Shard │             │
│  │Pool  │ │Pool  │ │Pool  │             │
│  │  0   │ │  1   │ │  2   │             │
│  └──┬───┘ └──┬───┘ └──┬───┘             │
└─────┼────────┼────────┼─────────────────┘
      │        │        │
      v        v        v
 ┌─────────┐ ┌─────────┐ ┌─────────┐
 │  Shard  │ │  Shard  │ │  Shard  │
 │    0    │ │    1    │ │    2    │
 │(5440)   │ │(5441)   │ │(5442)   │
 └─────────┘ └─────────┘ └─────────┘
```

## Key Features

### 1. **Hash-Based Sharding**
- Each key is hashed (MD5) and modulo'd by number of shards
- Ensures consistent routing: same key → same shard
- Provides good distribution across shards
- Formula: `shard_id = hash(key) % num_shards`

### 2. **Shard Router**
- Automatically routes writes to the correct shard
- Routes reads to the correct shard (after cache miss)
- Transparent to the application layer

### 3. **Write Scalability**
- Writes distributed across multiple databases
- Each shard handles a subset of the data
- Linear scalability: 3 shards = ~3x write capacity

### 4. **Cache-Aside Pattern**
- First read: Cache miss → Read from correct shard → Populate cache
- Subsequent reads: Cache hit → Return from Redis
- Write operation: Invalidate cache to ensure consistency

### 5. **Connection Pooling**
- Separate connection pool for each shard
- Configurable pool sizes for optimal resource usage
- Reuses connections for better performance

## Components

- **FastAPI**: Web framework with async support
- **PostgreSQL 15-alpine**: 3 independent database shards (ports 5440, 5441, 5442)
- **Redis 7-alpine**: Distributed cache (port 6381)
- **psycopg3**: PostgreSQL adapter with connection pooling
- **Hash Function**: MD5 for consistent shard routing
- **Docker Compose**: Container orchestration

## Configuration

Environment variables (see `.env.example`):

```env
SHARD_0_URL=postgresql://dbuser:dbpassword@localhost:5440/appdb_shard_0
SHARD_1_URL=postgresql://dbuser:dbpassword@localhost:5441/appdb_shard_1
SHARD_2_URL=postgresql://dbuser:dbpassword@localhost:5442/appdb_shard_2
REDIS_URL=redis://localhost:6381
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
CACHE_TTL=300
NUM_SHARDS=3
```

## Setup and Running

### Option 1: With Docker (Recommended)

```bash
# Start all services (3 shards, redis, api)
docker-compose up --build -d

# View logs
docker-compose logs -f api

# Check health
curl http://localhost:8004/health

# Stop services
docker-compose down
```

### Option 2: Without Docker

Requirements:
- Python 3.11+
- PostgreSQL 15+ (three separate instances)
- Redis 7+

```bash
# Install dependencies
pip install -r requirements.txt

# Set up three PostgreSQL instances on ports 5440, 5441, 5442
# Create databases: appdb_shard_0, appdb_shard_1, appdb_shard_2

# Update .env with your database URLs
cp .env.example .env
# Edit .env with your connection strings

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8004
```

## API Endpoints

### Write Data (Sharded)
```bash
POST /write
{
  "key": "user:123",
  "value": "John Doe"
}

Response:
{
  "success": true,
  "key": "user:123",
  "shard_id": 1,
  "message": "Data written successfully to shard 1"
}
```

### Read Data (from Cache or Shard)
```bash
GET /read/{key}

Response:
{
  "success": true,
  "key": "user:123",
  "value": "John Doe",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00",
  "from_cache": true,
  "shard_id": 1
}
```

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "layer": "4-db-sharding",
  "shards": {
    "shard_0": "healthy",
    "shard_1": "healthy",
    "shard_2": "healthy"
  },
  "cache": "healthy"
}
```

### Statistics
```bash
GET /stats

Response:
{
  "cache_available": true,
  "cache_hits": 150,
  "cache_misses": 50,
  "cache_keys": 45,
  "cache_hit_rate": 75.0,
  "num_shards": 3,
  "shard_pool_sizes": {
    "shard_0": 2,
    "shard_1": 2,
    "shard_2": 2
  },
  "shard_distribution": {
    "shard_0": 15,
    "shard_1": 18,
    "shard_2": 12
  }
}
```

## How It Works

### Write Flow
1. Client sends POST /write with key-value
2. Shard router hashes the key: `shard_id = hash(key) % 3`
3. Data written to the determined **shard database**
4. Cache invalidated for the key
5. Success response includes `shard_id`

### Read Flow (Cache Miss)
1. Client sends GET /read/{key}
2. Check Redis cache → **MISS**
3. Shard router determines shard: `shard_id = hash(key) % 3`
4. Query the **correct shard database**
5. Store result in Redis cache (TTL: 300s)
6. Return data with `from_cache: false`, `shard_id: N`

### Read Flow (Cache Hit)
1. Client sends GET /read/{key}
2. Check Redis cache → **HIT**
3. Return cached data immediately
4. Return data with `from_cache: true`

## Sharding Details

### Hash Function
- Algorithm: MD5 hash of key
- Converts to integer, then modulo by number of shards
- Provides uniform distribution across shards
- Deterministic: same key always goes to same shard

### Shard Distribution
With 100 keys and 3 shards:
- Shard 0: ~33 keys
- Shard 1: ~33 keys
- Shard 2: ~34 keys

Distribution is probabilistically balanced.

### Adding Shards (Resharding)
**Important**: Adding shards requires data migration!
- Current: `shard_id = hash(key) % 3`
- After adding shard 3: `shard_id = hash(key) % 4`
- Keys will map to different shards → requires full reshard
- Approaches: consistent hashing, virtual shards, or full migration

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Read Latency (Cache Hit) | ~1-2ms |
| Read Latency (Cache Miss) | ~10-20ms |
| Write Latency | ~15-30ms |
| Read Throughput | 10,000+ req/s (cached) |
| Write Throughput | 3,000+ req/s (3 shards) |
| Write Scalability | Linear with shards |

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_sharding.py

# Run with coverage
pytest --cov=app --cov-report=html
```

Expected output: **26 tests** covering:
- API endpoints (write, read, health, stats)
- Sharding logic (consistency, distribution, isolation)
- Cache behavior (hit, miss, invalidation)
- Concurrent operations
- Edge cases

## Trade-offs

### Advantages ✅
- **Linear write scalability**: Add shards to scale writes
- **Large dataset support**: Data distributed across shards
- **Independent shard failures**: One shard down doesn't affect others
- **Fast cached reads**: Sub-millisecond response times

### Disadvantages ❌
- **Complex operations**: Cross-shard queries are difficult/expensive
- **Resharding complexity**: Adding/removing shards requires data migration
- **No foreign keys across shards**: Data integrity harder to maintain
- **Transaction limitations**: Can't have ACID transactions across shards
- **Operational overhead**: Managing multiple databases

## When to Use

Use this architecture when:
- Dataset exceeds single database capacity
- Write throughput exceeds single database limit
- Data can be naturally partitioned by key (users, tenants, etc.)
- Cross-shard queries are rare or can be avoided

Consider simpler architectures (Layer 1-3) if:
- Dataset fits in a single database
- Write volume is manageable on one database
- You need complex joins or transactions across all data
- Operational simplicity is a priority

## Sharding Strategies

### Hash-Based (Implemented)
- **Pro**: Uniform distribution, simple
- **Con**: Resharding is hard, can't do range queries

### Range-Based (Alternative)
- **Pro**: Range queries efficient, easier to add shards
- **Con**: Risk of hot shards, uneven distribution
- **Example**: Users 1-1000 → Shard 0, Users 1001-2000 → Shard 1

### Geo-Based (Alternative)
- **Pro**: Low latency for regional users
- **Con**: Uneven distribution by region
- **Example**: US users → Shard 0, EU users → Shard 1, Asia users → Shard 2

## Next Steps

To further scale this architecture:
- **Layer 5**: Add multi-tier caching (L1/L2 cache)
- **Layer 6**: Implement write buffering with message queues
- **Layer 7**: Separate read/write models with CQRS
- **Layer 8**: Use polyglot persistence (different DB types per use case)

## Monitoring

Key metrics to monitor:

```bash
# Check shard distribution
GET /stats

# Monitor shard health
GET /health

# Check cache hit rate
GET /stats
# Look for cache_hit_rate > 60%

# Monitor per-shard load (use database monitoring tools)
# Watch for hot shards (uneven distribution)
```

## Common Issues

### Hot Shards
- **Problem**: One shard gets more traffic than others
- **Solution**: Review sharding key, consider consistent hashing

### Resharding
- **Problem**: Need to add/remove shards
- **Solution**: Plan for consistent hashing or virtual shards from start

### Cross-Shard Queries
- **Problem**: Need to query data across all shards
- **Solution**: Use application-level scatter-gather, or denormalize data
