# Layer 8 - Polyglot Persistence

## Architecture

This layer implements polyglot persistence - using different database technologies for different data access patterns:

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│      FastAPI API Server      │
└───┬──────────────┬───────┬───┘
    │              │       │
    │              │       │
    ▼              ▼       ▼
┌────────┐   ┌──────────┐ ┌────────────┐
│ Redis  │   │ MongoDB  │ │ PostgreSQL │
│ Cache  │   │ Document │ │ ACID       │
│        │   │ Store    │ │ Relational │
└────────┘   └──────────┘ └────────────┘
  (Fast)      (Flexible)    (Consistent)
```

## Database Selection Strategy

### PostgreSQL - Transactional Data
**Use For:**
- Financial transactions
- User accounts
- Orders and payments
- Any data requiring ACID guarantees
- Relational data with foreign keys

**Characteristics:**
- ACID compliance
- Strong consistency
- JSONB for semi-structured data
- Complex queries with JOINs
- Referential integrity

### MongoDB - Document Store
**Use For:**
- User profiles
- Product catalogs
- Content management
- Event logs
- Any data with flexible/evolving schema

**Characteristics:**
- Flexible schema
- Fast writes
- Horizontal scalability
- Rich query language
- Nested documents

### Redis - Cache Layer
**Use For:**
- Caching frequently accessed data
- Session storage
- Real-time analytics
- Rate limiting
- Temporary data

**Characteristics:**
- In-memory (extremely fast)
- Key-value store
- TTL support
- Pub/Sub capabilities
- Data structures (lists, sets, sorted sets)

## Performance Characteristics

- **Write Speed**: 🟢🟢🟢🟢 Fast - optimized per workload
- **Read Speed**: 🟢🟢🟢🟢🟢 Very Fast - cache + specialized DBs
- **Scalability**: 🟢🟢🟢🟢 High - scale each DB independently
- **Complexity**: 🟡🟡🟡🟡 High - multiple systems to manage
- **Flexibility**: 🟢🟢🟢🟢🟢 Excellent - right tool for each job

## Trade-offs

### Advantages
- Optimal database for each use case
- Better performance than one-size-fits-all
- Independent scaling of each database
- Reduced lock contention
- Specialized optimizations per workload
- Cost-effective (use expensive DBs only where needed)

### Disadvantages
- Operational complexity (3+ database systems)
- Distributed transactions are challenging
- More monitoring and maintenance required
- Data consistency across systems
- Higher infrastructure costs
- Steeper learning curve

## Use Cases

- **E-commerce platforms**: PostgreSQL for orders, MongoDB for products, Redis for cart
- **Social media**: PostgreSQL for relationships, MongoDB for posts, Redis for feeds
- **SaaS applications**: PostgreSQL for billing, MongoDB for user data, Redis for sessions
- **Analytics platforms**: PostgreSQL for metadata, MongoDB for events, Redis for aggregations
- **Content platforms**: PostgreSQL for users, MongoDB for articles, Redis for trending

## Running with Docker

```bash
# Start all services (PostgreSQL, MongoDB, Redis, API)
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api

# Access MongoDB shell
docker-compose exec mongodb mongosh -u mongouser -p mongopassword

# Access PostgreSQL shell
docker-compose exec postgres psql -U dbuser -d transactional_db

# Access Redis CLI
docker-compose exec redis redis-cli

# Run tests
docker-compose exec api pytest -v

# Stop services
docker-compose down
```

## Running without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL on port 5449
# Start MongoDB on port 27017
# Start Redis on port 6386

# Start the API
uvicorn app.main:app --reload --port 8008

# Run tests
pytest -v
```

## API Endpoints

### Write Transaction (PostgreSQL)
```bash
POST /write/transaction
{
  "user_id": "user123",
  "amount": 99.99,
  "transaction_type": "purchase"
}

Response:
{
  "success": true,
  "transaction_id": 42,
  "message": "Transaction written to PostgreSQL",
  "stored_in": "PostgreSQL"
}
```

### Write Document (MongoDB)
```bash
POST /write/document
{
  "key": "user_profile_123",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "preferences": {
      "theme": "dark",
      "notifications": true
    }
  }
}

Response:
{
  "success": true,
  "key": "user_profile_123",
  "data": {...},
  "from_cache": false,
  "stored_in": "MongoDB"
}
```

### Read Transactions (PostgreSQL + Redis Cache)
```bash
GET /read/transaction/{user_id}

Response:
{
  "success": true,
  "key": "user123",
  "value": [
    {
      "id": 42,
      "user_id": "user123",
      "amount": 99.99,
      "transaction_type": "purchase",
      "created_at": "2025-12-16T10:30:00"
    }
  ],
  "source": "postgres"  # or "cache" on subsequent reads
}
```

### Read Document (MongoDB + Redis Cache)
```bash
GET /read/document/{key}

Response:
{
  "success": true,
  "key": "user_profile_123",
  "data": {...},
  "from_cache": true,
  "stored_in": "Redis (cache)"  # or "MongoDB" if cache miss
}
```

### Statistics
```bash
GET /stats

Response:
{
  "postgres_pool_size": 10,
  "mongodb_connections": 1,
  "cache_keys": 245,
  "total_transactions": 1542,
  "total_documents": 3891
}
```

### Health Check
```bash
GET /health

Response:
{
  "status": "healthy",
  "layer": "8-polyglot-persistence",
  "databases": ["PostgreSQL", "MongoDB", "Redis"]
}
```

## Data Flow Examples

### E-commerce Order Flow
```
1. User creates order:
   POST /write/transaction (user_id, amount, type="purchase")
   → Stored in PostgreSQL (ACID compliance)

2. User profile updated:
   POST /write/document (key="user:123", data={orders_count: 15})
   → Stored in MongoDB (flexible schema)
   → Cache invalidated in Redis

3. Read user's order history:
   GET /read/transaction/user:123
   → Check Redis cache first
   → If miss, query PostgreSQL
   → Cache result in Redis (60s TTL)
```

### Content Platform Flow
```
1. User publishes article:
   POST /write/document (key="article:456", data={title, content, ...})
   → Stored in MongoDB (flexible content structure)

2. User subscription transaction:
   POST /write/transaction (user_id, amount, type="subscription")
   → Stored in PostgreSQL (billing data)

3. Read article:
   GET /read/document/article:456
   → Check Redis cache (5 min TTL)
   → If miss, fetch from MongoDB
   → Cache in Redis
```

## Database Schemas

### PostgreSQL Schema (Transactional)
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);
```

### MongoDB Schema (Flexible)
```javascript
// No fixed schema - examples:

// User profile
{
  key: "user_profile_123",
  data: {
    name: "John Doe",
    email: "john@example.com",
    age: 30,
    preferences: { ... }
  }
}

// Product catalog
{
  key: "product_456",
  data: {
    name: "Laptop",
    price: 999.99,
    specs: {
      ram: "16GB",
      storage: "512GB SSD"
    },
    reviews: [...]
  }
}
```

### Redis Cache Keys
```
# Transaction cache
transactions:{user_id} → JSON array (60s TTL)

# Document cache
doc:{key} → JSON object (300s TTL)
```

## Testing

The test suite covers:
- Writing transactions to PostgreSQL
- Writing documents to MongoDB
- Reading with Redis caching
- Cache invalidation
- Flexible schema in MongoDB
- ACID compliance in PostgreSQL
- Data integrity across systems
- Statistics aggregation
- Error handling

Run tests:
```bash
# With Docker
docker-compose exec api pytest -v

# Without Docker
pytest -v
```

Test results: **20 comprehensive tests** ✅

## Configuration

Environment variables (see `.env`):
- `POSTGRES_URL`: PostgreSQL connection string
- `MONGODB_URL`: MongoDB connection string
- `REDIS_URL`: Redis connection string
- `DB_POOL_MIN_SIZE`: PostgreSQL pool minimum (default: 2)
- `DB_POOL_MAX_SIZE`: PostgreSQL pool maximum (default: 10)
- `CACHE_TTL`: Redis cache TTL in seconds (default: 300)

## Decision Matrix

| Data Type | PostgreSQL | MongoDB | Redis |
|-----------|------------|---------|-------|
| Financial transactions | ✅ Best | ❌ No | ❌ No |
| User profiles | 🟡 Possible | ✅ Best | ❌ No |
| Product catalog | 🟡 Possible | ✅ Best | ❌ No |
| Session data | ❌ No | 🟡 Possible | ✅ Best |
| Real-time counters | ❌ No | ❌ No | ✅ Best |
| Complex JOINs | ✅ Best | ❌ No | ❌ No |
| Flexible schema | 🟡 JSONB | ✅ Best | 🟡 Limited |
| Horizontal scaling | 🟡 Complex | ✅ Easy | ✅ Easy |

## Monitoring & Operations

### Health Checks
```bash
# PostgreSQL
docker-compose exec postgres pg_isready

# MongoDB
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Redis
docker-compose exec redis redis-cli ping
```

### Performance Monitoring
```bash
# PostgreSQL connections
docker-compose exec postgres psql -U dbuser -d transactional_db -c "SELECT count(*) FROM pg_stat_activity;"

# MongoDB stats
docker-compose exec mongodb mongosh -u mongouser -p mongopassword --eval "db.stats()"

# Redis info
docker-compose exec redis redis-cli INFO stats
```

### Backup Strategies
```bash
# PostgreSQL backup
pg_dump -U dbuser transactional_db > backup.sql

# MongoDB backup
mongodump --uri="mongodb://mongouser:mongopassword@localhost:27017/"

# Redis backup
redis-cli BGSAVE
```

## Key Learnings

1. **Right Tool for the Job**: Each database excels at specific workloads
2. **Complexity Trade-off**: More databases = more operational overhead
3. **Data Consistency**: Managing consistency across systems is challenging
4. **Independent Scaling**: Each DB can scale based on its workload
5. **Cost Optimization**: Use expensive features only where needed
6. **Cache Everything**: Redis reduces load on both PostgreSQL and MongoDB

## Comparison with Previous Layers

| Metric | L7 (CQRS) | L8 (Polyglot) |
|--------|-----------|---------------|
| DB Types | 2 (Write/Read PostgreSQL) | 3 (PostgreSQL/MongoDB/Redis) |
| Flexibility | Moderate | High |
| Complexity | High | Higher |
| Workload Optimization | Read vs Write | By data type |
| Schema Flexibility | Fixed SQL | Mixed (SQL + NoSQL) |
| Cost | Moderate | Higher |

## Next Layer

Layer 9 introduces **Global Distributed Databases** with multi-region replication, geo-routing, and disaster recovery for worldwide scale.
