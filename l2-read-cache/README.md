# Layer 2 - Read Cache (Cache-Aside)

Architecture with PostgreSQL, connection pooling, and Redis caching. Implements cache-aside pattern for massive read latency reduction.

## Architecture

```
READ  → API → Redis Cache → PostgreSQL
WRITE → API → PostgreSQL → Cache Invalidate
```

## Components

- **FastAPI**: REST API with write/read endpoints + cache stats
- **PostgreSQL 15**: Database with connection pooling
- **Redis 7**: In-memory cache (alpine)
- **Docker**: Containerized services

## Cache-Aside Pattern

### Read Flow:
1. Check cache first
2. If cache miss → read from database
3. Store result in cache (TTL: 5 minutes)
4. Return to client

### Write Flow:
1. Write to database
2. Invalidate cache for that key
3. Next read will repopulate cache

## Key Improvements over Layer 1

- 🔥 **Massive read latency reduction** (microseconds vs milliseconds)
- 🔥 **60-90% reduction in database load**
- ✅ Cache hit rate tracking
- ✅ TTL-based cache expiration
- ✅ Automatic cache invalidation on writes

## API Endpoints

### Write Data
```bash
POST /write
{
  "key": "my_key",
  "value": "my_value"
}
```

### Read Data
```bash
GET /read/{key}
# Response includes from_cache: true/false
```

### Cache Statistics
```bash
GET /cache-stats
# Returns: hits, misses, hit_rate, keys count
```

### Health Check
```bash
GET /health
```

## Setup and Run

### With Docker

1. Start all services:
```bash
docker-compose up --build -d
```

2. API will be available at http://localhost:8002

### Without Docker

1. Install and start PostgreSQL on port 5434
2. Install and start Redis on port 6379

3. Create database:
```bash
createdb -U postgres -p 5434 appdb
```

4. Update `.env` file with your credentials

5. Install dependencies and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# Make sure services are running
docker-compose up -d

# Copy tests to container and run
docker cp tests l2-read-cache-api-1:/app/
docker cp pytest.ini l2-read-cache-api-1:/app/
docker-compose exec api pytest tests/ -v
```

## Configuration

Environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `DB_POOL_MIN_SIZE`: Minimum pool size (default: 2)
- `DB_POOL_MAX_SIZE`: Maximum pool size (default: 10)
- `CACHE_TTL`: Cache TTL in seconds (default: 300)

## Characteristics

- **Read Latency**: 🔥 Microseconds (cache hit) / Milliseconds (cache miss)
- **Write Latency**: Similar to Layer 1 (+ cache invalidation overhead)
- **Throughput**: 🔼 Much higher for reads
- **Database Load**: 🔽 60-90% reduction
- **Scalability**: Read-heavy workloads scale well
- **Consistency**: Eventual (cache TTL)

## Use Cases

- Read-heavy applications
- Social media feeds
- Product catalogs
- API responses with slow-changing data
- Applications with high read-to-write ratio

## Cache Performance

Typical cache hit rates:
- First read: 0% (cache miss)
- Subsequent reads: ~90-95% (cache hits)
- After writes: Temporary dip (cache invalidation)
