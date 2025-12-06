# Layer 7 - CQRS (Command Query Responsibility Segregation)

## Architecture

This layer implements the CQRS pattern, separating read and write operations into different databases:

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ├──── POST /write ────┐
       │                     ▼
       │              ┌──────────────┐
       │              │  Write API   │
       │              └──────┬───────┘
       │                     │
       │              ┌──────▼───────┐      ┌─────────────┐
       │              │  Write DB    │──────│ Redis       │
       │              │  (OLTP)      │      │ Streams     │
       │              └──────────────┘      └──────┬──────┘
       │                                            │
       │                                            │ Events
       │                                            │
       │              ┌──────────────┐      ┌──────▼──────┐
       │              │  Read DB     │◄─────│ Projector   │
       │              │  (OLAP)      │      │ Service     │
       │              └──────┬───────┘      └─────────────┘
       │                     │
       └──── GET /read ──────┘
```

## Components

### Write Database (OLTP)
- Normalized schema optimized for transactional writes
- Stores commands as they arrive
- Fast writes with referential integrity

### Read Database (OLAP)
- Denormalized schema optimized for queries
- Includes aggregated fields (read_count, write_count)
- Eventual consistency with write database

### Event Stream (Redis Streams)
- Publishes domain events for all write operations
- Enables asynchronous projection to read database
- Provides audit trail of all changes

### Projector Service
- Background worker that reads events from Redis Streams
- Projects changes from write DB to read DB
- Updates denormalized read models

## Performance Characteristics

- **Write Speed**: 🟢🟢🟢🟢 Fast - optimized OLTP writes
- **Read Speed**: 🟢🟢🟢🟢🟢 Very Fast - denormalized read models
- **Consistency**: 🟡 Eventual - small delay between write and read
- **Scalability**: 🟢🟢🟢🟢 High - independent scaling of read/write
- **Complexity**: 🟡🟡🟡 Moderate - requires event projection

## Trade-offs

### Advantages
- Independent optimization of read and write workloads
- Can scale read and write databases independently
- Read models tailored for specific query patterns
- Event sourcing provides audit trail
- Better performance than single database for read-heavy workloads

### Disadvantages
- Eventual consistency - reads may lag behind writes
- Increased complexity with separate databases
- Requires event projection infrastructure
- Higher operational overhead (more services to manage)
- Need to handle projection failures

## Use Cases

- **E-commerce platforms**: Heavy read traffic for product catalogs, focused writes for orders
- **Content platforms**: Millions of reads, fewer writes (YouTube, Medium)
- **Analytics dashboards**: Complex read queries, simpler write operations
- **Social media feeds**: High read volume with targeted writes
- **Reporting systems**: Read-optimized aggregations separated from operational writes

## Running with Docker

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View projector logs
docker-compose logs -f projector

# Run tests
docker-compose exec api pytest -v

# Stop services
docker-compose down
```

## Running without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (write DB on port 5447, read DB on port 5448)
# Start Redis on port 6384

# Start the projector service
python -m app.projector &

# Start the API
uvicorn app.main:app --reload --port 8007

# Run tests
pytest -v
```

## API Endpoints

### Write Command
```bash
POST /write
{
  "key": "user:123",
  "value": "John Doe"
}
```

### Read Query
```bash
GET /read/{key}
```

### Statistics
```bash
GET /stats
```

### Health Check
```bash
GET /health
```

## Testing

The test suite covers:
- Write command processing
- Event publication to Redis Streams
- Event projection to read database
- Eventual consistency guarantees
- Read query from denormalized database
- Write/read count tracking
- Database separation
- Concurrent operations

## Configuration

Environment variables (see `.env`):
- `WRITE_DB_URL`: PostgreSQL connection for write database
- `READ_DB_URL`: PostgreSQL connection for read database
- `REDIS_URL`: Redis connection for event streaming
- `DB_POOL_MIN_SIZE`: Minimum connection pool size
- `DB_POOL_MAX_SIZE`: Maximum connection pool size
- `EVENT_STREAM_NAME`: Redis stream name for events
- `PROJECTOR_BATCH_SIZE`: Events to process per batch
- `PROJECTOR_POLL_INTERVAL`: Polling interval in seconds

## Database Schemas

### Write DB (Normalized)
```sql
CREATE TABLE commands (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_commands_key ON commands(key);
```

### Read DB (Denormalized)
```sql
CREATE TABLE records (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_count INTEGER DEFAULT 0,
    write_count INTEGER DEFAULT 0
);
```

## Key Learnings

1. **Separation of Concerns**: Read and write models serve different purposes
2. **Eventual Consistency**: Acceptable trade-off for most applications
3. **Event Sourcing**: Natural fit with CQRS for maintaining consistency
4. **Independent Scaling**: Can scale read replicas without affecting writes
5. **Denormalization**: Read models can be optimized for specific queries

## Next Layer

Layer 8 will introduce **Polyglot Persistence**, using different database types for different data access patterns (SQL for transactional data, MongoDB for flexible schemas, etc.).
