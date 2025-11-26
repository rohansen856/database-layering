# Layer 1 - DB + Connection Pooling

Architecture with PostgreSQL and connection pooling. Improves throughput and stability by reusing database connections.

## Architecture

```
Client → FastAPI → Connection Pool → PostgreSQL
```

## Components

- **FastAPI**: REST API with 2 endpoints (write, read) + pool stats
- **PostgreSQL 15**: Single database instance
- **Connection Pool**: psycopg pool (min: 2, max: 10 connections)
- **Docker**: Containerized database and API

## Key Improvements over Layer 0

- ✅ Connection pooling eliminates connection setup overhead
- ✅ Better concurrency handling
- ✅ More stable under load
- ✅ Configurable pool size

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
```

### Pool Statistics
```bash
GET /pool-stats
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

2. API will be available at http://localhost:8001

### Without Docker

1. Install and start PostgreSQL locally on port 5433

2. Create database:
```bash
createdb -U postgres -p 5433 appdb
```

3. Update `.env` file with your database credentials

4. Install dependencies and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# Make sure services are running
docker-compose up -d

# Copy tests to container and run
docker cp tests l1-connection-pooling-api-1:/app/
docker cp pytest.ini l1-connection-pooling-api-1:/app/
docker-compose exec api pytest tests/ -v
```

## Configuration

Environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `DB_POOL_MIN_SIZE`: Minimum pool size (default: 2)
- `DB_POOL_MAX_SIZE`: Maximum pool size (default: 10)

## Characteristics

- **Latency**: Reduced (no connection overhead)
- **Throughput**: 🔼 Higher (concurrent requests handled better)
- **Scalability**: Still limited to single DB
- **Fault Tolerance**: ❌ (single point of failure)
- **Stability**: 🔼 Better (pool manages connections)

## Use Cases

- Production APIs with moderate traffic
- Applications requiring concurrent database access
- Services where connection setup time is significant
