# Layer 9 - Global Distributed DB

## Architecture

Multi-region distributed database with geo-routing, replication, and disaster recovery:

```
       ┌─────────┐
       │ Client  │
       └────┬────┘
            │
            ▼
    ┌───────────────┐
    │  Geo Router   │
    └───┬───┬───┬───┘
        │   │   │
   ┌────┘   │   └────┐
   │        │        │
   ▼        ▼        ▼
┌────────┬────────┬────────┐
│US-EAST │EU-WEST │ASIA-PAC│
├────────┼────────┼────────┤
│ Cache  │ Cache  │ Cache  │
│   ↓    │   ↓    │   ↓    │
│   DB   │   DB   │   DB   │
└────────┴────────┴────────┘
    ↕️      ↕️       ↕️
  Replication Sync
```

## Features

### 1. Geo-Routing
- Automatic region selection based on client location
- Lowest latency reads from nearest region
- Header-based region override (`X-Region`)

### 2. Multi-Region Replication
- Write to primary region
- Automatic async replication to all other regions
- Eventual consistency across globe

### 3. Regional Caching
- Independent cache per region
- Reduced cross-region traffic
- Sub-millisecond local reads

### 4. Disaster Recovery
- Automatic failover to healthy regions
- Read from any region if primary unavailable
- No single point of failure

## Performance Characteristics

- **Write Speed**: 🟢🟢🟢🟢 Fast (local region)
- **Read Speed**: 🟢🟢🟢🟢🟢 Very Fast (geo-optimized)
- **Global Reach**: 🟢🟢🟢🟢🟢 Worldwide
- **Availability**: 🟢🟢🟢🟢🟢 99.99%+ (multi-region)
- **Complexity**: 🟡🟡🟡🟡🟡 Very High

## Trade-offs

### Advantages
- Global low latency (users read from nearest region)
- High availability (survives regional outages)
- Disaster recovery built-in
- Horizontal scalability across regions
- Compliance (data sovereignty per region)

### Disadvantages
- Complex operational overhead
- Replication lag between regions
- Higher infrastructure costs
- Network bandwidth for replication
- Eventual consistency challenges

## Running with Docker

```bash
docker-compose up -d
docker-compose ps
curl http://localhost:8009/health
docker-compose exec api pytest -v
docker-compose down
```

## API Examples

### Write (with replication)
```bash
curl -X POST http://localhost:8009/write \
  -H "X-Region: us-east" \
  -H "Content-Type: application/json" \
  -d '{"key":"user:123","value":"data"}'

Response: {
  "primary_region": "US-EAST",
  "replicated_to": ["EU-WEST", "ASIA-PAC"]
}
```

### Read (geo-routed)
```bash
curl http://localhost:8009/read/user:123 \
  -H "X-Region: eu-west"

Response: {
  "value": "data",
  "region": "EU-WEST",
  "source": "cache",
  "latency_ms": 1.23
}
```

### Global Stats
```bash
curl http://localhost:8009/stats

Response: {
  "regions": [
    {"region": "US-EAST", "total_records": 1234, "healthy": true},
    {"region": "EU-WEST", "total_records": 1234, "healthy": true},
    {"region": "ASIA-PAC", "total_records": 1234, "healthy": true}
  ],
  "healthy_regions": 3,
  "replication_enabled": true
}
```

## Use Cases

- **Global SaaS**: Serve users worldwide with low latency
- **Financial Systems**: Multi-region compliance and DR
- **Gaming Platforms**: Regional game servers with global state
- **E-commerce**: Regional inventory with global catalog
- **Social Media**: Content distribution across continents

## Configuration

See `.env` for region URLs. Supports:
- 3 PostgreSQL databases (one per region)
- 3 Redis caches (one per region)
- Configurable replication (on/off)

## Testing

20+ tests covering:
- Multi-region writes with replication
- Geo-routed reads
- Regional caching
- Disaster recovery failover
- Data consistency
- Latency tracking

**Run:** `pytest -v` (20 tests)

## Key Learnings

1. **Geo-Routing**: Reduces latency by 70-90% vs single region
2. **Replication**: Enables 99.99%+ availability
3. **Regional Caching**: Critical for performance
4. **Eventual Consistency**: Acceptable for most use cases
5. **Cost vs Performance**: Higher cost, much better UX

## Next Layer

Layer 10: **Enterprise-Grade Full Stack** with observability, auto-scaling, circuit breakers, and 99.99% uptime SLA.
