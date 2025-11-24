# Layer 0 - Single DB

Basic architecture with a single PostgreSQL database. No connection pooling, no caching, no replication.

## Architecture

```
Client → FastAPI → PostgreSQL
```

## Components

- **FastAPI**: REST API with 2 endpoints (write, read)
- **PostgreSQL 15**: Single database instance
- **Docker**: Containerized database

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

### Health Check
```bash
GET /health
```

## Setup and Run

### With Docker

1. Start the database:
```bash
docker-compose up -d
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the API:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Without Docker

1. Install and start PostgreSQL locally

2. Create database:
```bash
createdb -U postgres appdb
```

3. Update `.env` file with your database credentials

4. Install dependencies and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# Make sure database is running
docker-compose up -d

# Run tests
pytest tests/ -v
```

## Characteristics

- **Latency**: High (every request hits the database)
- **Throughput**: Low (limited by single DB connection per request)
- **Scalability**: ❌ (single point of failure)
- **Fault Tolerance**: ❌ (no redundancy)

## Use Cases

- Local development
- Proof of concepts
- Hackathons
- Small internal tools
