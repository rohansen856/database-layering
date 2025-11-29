# Layer 3 - Read Replicas + Cache

This layer implements a read-scalable architecture using PostgreSQL streaming replication with read replicas and Redis caching.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌──────────┐        ┌───────────┐  │
│  │  Write   │        │   Read    │  │
│  │ Endpoint │        │ Endpoint  │  │
│  └────┬─────┘        └─────┬─────┘  │
│       │                    │         │
│       │                    v         │
│       │            ┌───────────────┐ │
│       │            │ Redis Cache   │ │
│       │            │  (Check TTL)  │ │
│       │            └───────┬───────┘ │
│       │                    │         │
│       │              Cache │ Cache   │
│       │               Miss │ Hit     │
│       v                    v         │
│  ┌──────────┐      ┌──────────────┐ │
│  │ Primary  │      │   Replica    │ │
│  │   Pool   │      │     Pool     │ │
│  └────┬─────┘      └──────┬───────┘ │
└───────┼───────────────────┼─────────┘
        │                   │
        v                   v
┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │───>│  PostgreSQL  │
│   Primary    │    │   Replica    │
│  (Port 5435) │    │  (Port 5436) │
└──────────────┘    └──────────────┘
  Streaming Replication
```

## Key Features

### 1. **Read Replica Pattern**
- **Writes** go to the PRIMARY database
- **Reads** come from the REPLICA database
- Streaming replication keeps replica in sync with primary
- Reduces load on primary database for read-heavy workloads

### 2. **Cache-Aside Pattern**
- First read: Cache miss → Read from REPLICA → Populate cache
- Subsequent reads: Cache hit → Return from Redis (fast!)
- Write operation: Invalidate cache to ensure consistency

### 3. **Connection Pooling**
- Separate connection pools for primary and replica
- Configurable pool sizes for optimal resource usage
- Reuses connections for better performance

## Components

- **FastAPI**: Web framework with async support
- **PostgreSQL 15-alpine**:
  - Primary (port 5435): Handles all writes
  - Replica (port 5436): Handles all reads
  - Streaming replication (wal_level=replica)
- **Redis 7-alpine**: Distributed cache (port 6380)
- **psycopg3**: PostgreSQL adapter with connection pooling
- **Docker Compose**: Container orchestration

## Configuration

Environment variables (see `.env.example`):

```env
PRIMARY_DATABASE_URL=postgresql://dbuser:dbpassword@localhost:5435/appdb
REPLICA_DATABASE_URL=postgresql://dbuser:dbpassword@localhost:5436/appdb
REDIS_URL=redis://localhost:6380
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
CACHE_TTL=300
```

## Setup and Running

### Option 1: With Docker (Recommended)

```bash
# Start all services (primary, replica, redis, api)
docker-compose up --build -d

# View logs
docker-compose logs -f api

# Check health
curl http://localhost:8003/health

# Stop services
docker-compose down
```

### Option 2: Without Docker

Requirements:
- Python 3.11+
- PostgreSQL 15+ (two instances for primary/replica)
- Redis 7+

```bash
# Install dependencies
pip install -r requirements.txt

# Set up two PostgreSQL instances with streaming replication
# Configure primary: wal_level=replica, max_wal_senders=3
# Configure replica: use pg_basebackup to clone from primary

# Update .env with your database URLs
cp .env.example .env
# Edit .env with your connection strings

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

## API Endpoints

### Write Data (to Primary)
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
  "message": "Data written successfully to primary"
}
```

### Read Data (from Replica + Cache)
```bash
GET /read/{key}

Response:
{
  "success": true,
  "key": "user:123",
  "value": "John Doe",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00",
  "from_cache": true,    # true if served from Redis
  "from_replica": false  # true if served from replica DB
}
```

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "layer": "3-read-replicas",
  "primary": "healthy",
  "replica": "healthy",
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
  "primary_pool_size": 2,
  "replica_pool_size": 2
}
```

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_replication.py

# Run with coverage
pytest --cov=app --cov-report=html
```

Expected output: **22 tests** covering:
- API endpoints (write, read, health, stats)
- Cache behavior (hit, miss, invalidation)
- Replication (primary to replica sync)
- Concurrent operations
- Edge cases (special characters, long values)

## How It Works

### Write Flow
1. Client sends POST /write
2. Data written to **PRIMARY database**
3. PostgreSQL streams changes to **REPLICA** (async)
4. Cache invalidated for the key
5. Success response returned

### Read Flow (Cache Miss)
1. Client sends GET /read/{key}
2. Check Redis cache → **MISS**
3. Query **REPLICA database**
4. Store result in Redis cache (TTL: 300s)
5. Return data with `from_cache: false`, `from_replica: true`

### Read Flow (Cache Hit)
1. Client sends GET /read/{key}
2. Check Redis cache → **HIT**
3. Return cached data immediately
4. Return data with `from_cache: true`, `from_replica: false`

## Replication Details

### Streaming Replication
- Primary has `wal_level=replica` for Write-Ahead Log streaming
- Replica connects as a replication client
- Initial setup: `pg_basebackup` clones primary's data directory
- Ongoing sync: WAL segments streamed continuously
- **Replication lag**: Typically <1 second

### Handling Replication Lag
- Application sleeps 2 seconds on startup for initial sync
- Tests include 0.5-1 second delays after writes
- Production apps should monitor `pg_stat_replication` view
- Consider using synchronous replication for critical data

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Read Latency (Cache Hit) | ~1-2ms |
| Read Latency (Cache Miss) | ~10-20ms |
| Write Latency | ~15-30ms |
| Replication Lag | <1s (typically) |
| Cache Hit Rate | 60-80% (typical) |
| Read Throughput | 10,000+ req/s (cached) |
| Write Throughput | 1,000+ req/s |

## Trade-offs

### Advantages ✅
- **Scalable reads**: Add more replicas as needed
- **Reduced primary load**: Reads offloaded to replicas
- **Fast cached reads**: Sub-millisecond response times
- **High availability**: Replica can be promoted if primary fails

### Disadvantages ❌
- **Complexity**: Multiple databases to manage
- **Replication lag**: Slight delay before reads see writes
- **Storage overhead**: Each replica is a full copy of data
- **Cache invalidation**: Must be handled correctly to avoid stale data

## When to Use

Use this architecture when:
- Read-to-write ratio is high (90:10 or better)
- You need to scale read throughput beyond a single database
- Cache hit rates are expected to be >50%
- Application can tolerate slight replication lag

Consider simpler architectures (Layer 1-2) if:
- Read volume is manageable on a single database
- Strong read-after-write consistency is required
- Infrastructure complexity is a concern

## Next Steps

To further scale this architecture:
- **Layer 4**: Add database sharding for write scalability
- **Layer 5**: Implement multi-tier caching (L1/L2)
- **Layer 6**: Add write buffering with message queues
- **Layer 7**: Separate read/write models with CQRS

## Monitoring

Key metrics to monitor:
```sql
-- Check replication lag (on primary)
SELECT
  client_addr,
  state,
  sent_lsn,
  write_lsn,
  flush_lsn,
  replay_lsn,
  sync_state
FROM pg_stat_replication;

-- Check replica lag in bytes
SELECT pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;
```

Cache metrics available via `/stats` endpoint.
