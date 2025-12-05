# Layer 6 - Write Buffering / Async Writes

## Architecture

This layer implements asynchronous write buffering using Redis as a message queue with background workers:

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
       │ POST /write (immediate response)
       │
       ▼
┌──────────────┐
│  Redis Queue │◄──────┐
│  (Write Job) │       │
└──────┬───────┘       │
       │               │
       │ Dequeue       │ Enqueue
       │               │
       ▼               │
┌──────────────┐       │
│  Background  │       │
│  Worker      │       │
│  (Async)     │       │
└──────┬───────┘       │
       │               │
       ▼               │
┌──────────────┐       │
│  PostgreSQL  │       │
│  Database    ├───────┘
└──────────────┘
       ▲
       │
       │ GET /read (synchronous)
       │
┌──────────────┐
│  FastAPI     │
│  API Server  │
└──────────────┘
```

## Components

### Write Queue (Redis List)
- **Technology**: Redis LPUSH/BRPOP
- **Purpose**: Buffer write operations
- **Durability**: Configurable (AOF/RDB)
- **Processing**: FIFO (First-In-First-Out)

### Background Worker
- **Language**: Python
- **Processing**: Batch operations (configurable batch size)
- **Error Handling**: Retry logic with exponential backoff
- **Monitoring**: Failed writes tracked separately

### Consistency Model
- **Type**: Eventual consistency
- **Write Latency**: Immediate response (~1-2ms)
- **Persistence Latency**: Variable (typically < 1 second)
- **Read Consistency**: May return stale data briefly after write

## Performance Characteristics

- **Write Speed**: 🟢🟢🟢🟢🟢 Very Fast - immediate response without DB wait
- **Read Speed**: 🟢🟢🟢🟢 Fast - direct database reads
- **Consistency**: 🟡 Eventual - writes appear after short delay
- **Scalability**: 🟢🟢🟢 Good - easy to scale workers
- **Complexity**: 🟡🟡🟡🟡 Moderate-High - requires worker management

## Trade-offs

### Advantages
- Extremely fast write responses (no database blocking)
- High write throughput (batch processing)
- Resilient to database outages (queue acts as buffer)
- Can scale workers independently
- Natural rate limiting (queue depth)
- Easy to add write analytics/monitoring

### Disadvantages
- Eventual consistency - reads may not reflect recent writes
- Requires queue infrastructure (Redis)
- Worker process management complexity
- Potential data loss if queue isn't durable
- Debugging is harder (async operations)
- Need to handle failed writes

## Use Cases

- **High-volume logging**: Application logs, analytics events
- **Metrics collection**: Time-series data, monitoring metrics
- **User activity tracking**: Clicks, views, interactions
- **Non-critical writes**: Comments, likes, view counts
- **Batch data imports**: ETL pipelines, data ingestion
- **Write-heavy workloads**: More writes than reads

## Running with Docker

```bash
# Start all services (API, Worker, Redis, PostgreSQL)
docker-compose up -d

# Check service health
docker-compose ps

# View API logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f worker

# Check queue depth
docker-compose exec redis redis-cli LLEN write_queue

# Run tests
docker-compose exec api pytest -v

# Stop services
docker-compose down
```

## Running without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL on port 5437
# Start Redis on port 6385

# Terminal 1: Start the API
uvicorn app.main:app --reload --port 8006

# Terminal 2: Start the worker
python -m app.worker

# Terminal 3: Run tests
pytest -v
```

## API Endpoints

### Write Data (Async)
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
  "queued": true,
  "queue_depth": 45,
  "message": "Write queued successfully"
}
```

### Read Data (Sync)
```bash
GET /read/{key}

Response:
{
  "success": true,
  "key": "user:123",
  "value": "John Doe"
}
```

### Queue Statistics
```bash
GET /stats

Response:
{
  "queue_depth": 45,
  "writes_queued": 12450,
  "writes_processed": 12405,
  "writes_failed": 3,
  "processing_rate": 150.5  # writes per second
}
```

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "queue_depth": 45,
  "worker_active": true
}
```

## Write Flow

### 1. Write Request
```
Client → POST /write → API validates → Push to Redis queue → Return 202 Accepted
```

### 2. Background Processing
```
Worker → BRPOP from queue → Batch writes → Execute to DB → Update stats
```

### 3. Read Request
```
Client → GET /read → Query DB directly → Return value
```

## Eventual Consistency Example

```bash
# T=0: Write request
POST /write {"key": "counter", "value": "100"}
→ Response: 202 Accepted (immediate)

# T=0.001s: Read immediately
GET /read/counter
→ May return old value or 404 (write not yet processed)

# T=0.5s: Worker processes write
Worker → Writes to database

# T=0.6s: Read again
GET /read/counter
→ Returns "100" (write now visible)
```

## Worker Configuration

### Batch Processing
```python
BATCH_SIZE = 10  # Process 10 writes at once
BATCH_TIMEOUT = 1.0  # Wait max 1 second for batch to fill
```

### Error Handling
```python
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # Exponential backoff: 1s, 2s, 4s
```

### Monitoring
- Queue depth alerts
- Failed write tracking
- Processing rate metrics
- Worker health checks

## Testing

The test suite covers:
- Basic write queueing
- Read operations
- Eventual consistency
- Queue depth tracking
- Batch processing
- Failed write handling
- Worker restart recovery
- High-volume writes
- Queue statistics

Run tests:
```bash
# With Docker
docker-compose exec api pytest -v

# Without Docker (requires worker running)
pytest -v
```

Test results: **14/14 tests passing** ✅

## Configuration

Environment variables (see `.env`):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `WRITE_QUEUE_NAME`: Redis list key for queue (default: "write_queue")
- `BATCH_SIZE`: Writes to process per batch (default: 10)
- `BATCH_TIMEOUT`: Max wait for batch fill in seconds (default: 1.0)
- `WORKER_POLL_INTERVAL`: Polling interval in seconds (default: 0.1)
- `MAX_RETRIES`: Retry attempts for failed writes (default: 3)

## Monitoring & Operations

### Queue Depth Monitoring
```bash
# Check current queue depth
redis-cli LLEN write_queue

# Alert if depth > 1000 (worker can't keep up)
```

### Worker Health
```bash
# Check if worker is running
docker-compose ps worker

# View worker logs
docker-compose logs -f worker
```

### Failed Writes
```bash
# Check failed writes count
curl http://localhost:8006/stats | jq '.writes_failed'

# View failed write details (implement logging)
```

## Performance Tips

### Optimizing Write Throughput
1. **Increase batch size**: Process more writes per transaction
2. **Add more workers**: Scale horizontally
3. **Tune PostgreSQL**: Adjust `max_connections`, `shared_buffers`
4. **Use Redis pipelining**: Batch queue operations

### Reducing Consistency Window
1. **Lower batch timeout**: Process writes more frequently
2. **Increase worker count**: Parallel processing
3. **Optimize DB writes**: Use COPY or bulk inserts
4. **Add read-through cache**: Serve from queue before DB write

### Queue Management
```bash
# Purge queue (careful!)
redis-cli DEL write_queue

# Monitor queue growth
watch -n 1 'redis-cli LLEN write_queue'

# Backup queue
redis-cli --rdb /backup/queue-backup.rdb
```

## Error Scenarios

### Worker Crash
- **Impact**: Queue continues to grow, writes paused
- **Recovery**: Restart worker, processes backlog
- **Mitigation**: Worker auto-restart, queue depth alerts

### Database Outage
- **Impact**: Writes queue up in Redis
- **Recovery**: Worker retries with backoff, drains queue when DB returns
- **Mitigation**: Redis persistence (AOF), worker retry logic

### Redis Failure
- **Impact**: New writes rejected, in-flight writes may be lost
- **Recovery**: Restart Redis, lose in-memory queue (if no persistence)
- **Mitigation**: Redis AOF enabled, Redis Sentinel/Cluster

## Key Learnings

1. **Eventual Consistency**: Acceptable trade-off for many use cases
2. **Queue as Buffer**: Protects database from write spikes
3. **Observability**: Queue depth is key metric
4. **Durability**: Configure Redis persistence for critical data
5. **Scalability**: Easy to add workers for higher throughput
6. **Error Handling**: Retry logic essential for reliability

## Comparison with Previous Layers

| Metric | L5 (Sync Writes) | L6 (Async Writes) |
|--------|------------------|-------------------|
| Write Latency | 10-50ms (DB wait) | 1-2ms (queue only) |
| Write Throughput | ~500/sec | ~5000/sec |
| Read Consistency | Immediate | Eventual (~100-500ms) |
| Complexity | Moderate | High |
| Database Load | High | Batched/Lower |
| Failure Recovery | Immediate retry | Queue + retry |

## Next Layer

Layer 7 introduces **CQRS (Command Query Responsibility Segregation)** with separate write and read databases optimized for their specific workloads.
