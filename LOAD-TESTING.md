# Load Testing Guide

This guide explains how to perform load testing on each database architecture layer using [oha](https://github.com/hatoo/oha), a modern HTTP load testing tool written in Rust.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Test Script Usage](#test-script-usage)
- [Manual Testing with oha](#manual-testing-with-oha)
- [Test Types](#test-types)
- [Interpreting Results](#interpreting-results)
- [Performance Comparison](#performance-comparison)
- [Best Practices](#best-practices)

## Prerequisites

### Install oha

**Using Cargo (Rust):**
```bash
cargo install oha
```

**Using Homebrew (macOS/Linux):**
```bash
brew install oha
```

**From Binary:**
Download from [GitHub Releases](https://github.com/hatoo/oha/releases)

### Verify Installation

```bash
oha --version
```

### Start Layer Services

Before testing, ensure the layer you want to test is running:

```bash
cd l<N>-<name>/
docker-compose up -d

# Wait for services to be healthy
sleep 15

# Verify health
curl http://localhost:800<N>/health
```

## Quick Start

### Test a Specific Layer

```bash
# Test Layer 5 with default settings
./load-test.sh 5

# Test Layer 2 with custom parameters
./load-test.sh -n 5000 -c 100 -d 30 2

# Test only write performance on Layer 0
./load-test.sh -t write 0

# Test only read performance on Layer 10
./load-test.sh -t read 10
```

### Test All Layers

```bash
# Test all layers with default settings
./load-test.sh

# Test all layers with custom parameters
REQUESTS=2000 CONCURRENCY=75 DURATION=15 ./load-test.sh
```

## Test Script Usage

### Command Syntax

```bash
./load-test.sh [OPTIONS] [LAYER_NUMBER]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-n NUM` | Number of requests (mutually exclusive with `-z`) | 1000 |
| `-c NUM` | Concurrency level | 50 |
| `-z SECONDS` | Duration in seconds (mutually exclusive with `-n`) | - |
| `-t TYPE` | Test type: `write`, `read`, `mixed`, `all` | `all` |
| `-r RATE` | Rate limit (requests/sec, 0=unlimited) | 0 |
| `-h` | Show help | - |

**Note**: You can use either `-n` (number of requests) OR `-z` (duration), but not both together.

### Examples

#### Basic Testing

```bash
# Test Layer 0 with defaults (1000 requests, 50 concurrency, 10s)
./load-test.sh 0

# Test Layer 5 with 5000 requests and 100 concurrent connections
./load-test.sh -n 5000 -c 100 5

# Run a 30-second load test on Layer 10
./load-test.sh -z 30 10
```

#### Test Type Specific

```bash
# Only test write performance on Layer 2
./load-test.sh -t write 2

# Only test read performance on Layer 5
./load-test.sh -t read 5

# Only test mixed workload on Layer 7
./load-test.sh -t mixed 7

# Test all operations on Layer 10
./load-test.sh -t all 10
```

#### High-Load Testing

```bash
# Stress test Layer 10 with high concurrency
./load-test.sh -n 10000 -c 200 10

# Sustained load test on Layer 5 (120 seconds)
./load-test.sh -z 120 -c 150 5
```

#### Rate-Limited Testing

```bash
# Test with rate limit of 100 requests/second (30 seconds)
./load-test.sh -r 100 -z 30 5
```

## Manual Testing with oha

### Write Performance Test

```bash
# Basic write test
oha -n 1000 -c 50 \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"key": "test_key", "value": "test_value"}' \
  http://localhost:8000/write

# High concurrency write test
oha -n 5000 -c 200 -z 30s \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"key": "stress_test_$RANDOM", "value": "value_$RANDOM"}' \
  http://localhost:8005/write

# Rate-limited write test
oha -n 1000 --qps 100 \
  -m POST \
  -H "Content-Type: application/json" \
  -d '{"key": "rate_test", "value": "value"}' \
  http://localhost:8002/write
```

### Read Performance Test

```bash
# First, write test data
curl -X POST http://localhost:8000/write \
  -H "Content-Type: application/json" \
  -d '{"key": "benchmark_key", "value": "benchmark_value"}'

# Basic read test
oha -n 1000 -c 50 \
  http://localhost:8000/read/benchmark_key

# High concurrency read test
oha -n 10000 -c 200 -z 30s \
  http://localhost:8005/read/benchmark_key

# Sustained read test
oha -z 60s -c 100 \
  http://localhost:8002/read/benchmark_key
```

### Health Check Load Test

```bash
# Test health endpoint performance
oha -n 5000 -c 100 \
  http://localhost:8000/health
```

### Custom Headers (Layer 10 - Enterprise)

```bash
# Layer 10 requires authentication
oha -n 1000 -c 50 \
  -m POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key" \
  -H "X-Client-ID: test-client" \
  -d '{"key": "auth_test", "value": "value"}' \
  http://localhost:8010/write
```

## Test Types

### 1. Write Test
- **Purpose**: Measure database write throughput and latency
- **Method**: POST requests to `/write` endpoint
- **Metrics**: Requests/sec, latency (p50, p95, p99)
- **Use Case**: Evaluate write scaling capabilities

### 2. Read Test
- **Purpose**: Measure read performance and cache effectiveness
- **Method**: GET requests to `/read/{key}` endpoint
- **Metrics**: Requests/sec, latency, cache hit rate
- **Use Case**: Evaluate caching layers and read scaling

### 3. Mixed Test (70% Read / 30% Write)
- **Purpose**: Simulate realistic workload
- **Method**: Concurrent read and write requests
- **Metrics**: Overall throughput, latency distribution
- **Use Case**: Real-world performance assessment

### 4. Stress Test
- **Purpose**: Find system limits and breaking points
- **Method**: Gradually increasing load
- **Metrics**: Max throughput, error rates
- **Use Case**: Capacity planning

## Interpreting Results

### Key Metrics

```
Summary:
  Success rate: 1.0000
  Total:        10.0234 secs
  Slowest:      0.1523 secs
  Fastest:      0.0012 secs
  Average:      0.0234 secs
  Requests/sec: 998.4123

Response time histogram:
  0.001 [1]     |
  0.016 [450]   |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.031 [350]   |■■■■■■■■■■■■■■■■■■■■■■■■
  0.046 [120]   |■■■■■■■■
  ...

Latency distribution:
  10% in 0.0123 secs
  25% in 0.0156 secs
  50% in 0.0234 secs
  75% in 0.0312 secs
  90% in 0.0445 secs
  95% in 0.0567 secs
  99% in 0.0891 secs
```

### What to Look For

1. **Success Rate**: Should be 1.0000 (100%)
   - Lower values indicate errors or timeouts

2. **Requests/sec**: Higher is better
   - Measures throughput capacity

3. **Latency (p50, p95, p99)**:
   - p50 (median): Typical user experience
   - p95: Experience for most users
   - p99: Worst-case for ~1% of requests

4. **Response Time Histogram**:
   - Should be left-skewed (most requests fast)
   - Long tail indicates performance issues

## Performance Comparison

### Expected Results by Layer

Based on 1000 requests, 50 concurrency:

| Layer | Read RPS | Write RPS | Read p99 | Write p99 | Notes |
|-------|----------|-----------|----------|-----------|-------|
| L0 - Single DB | 100-200 | 50-100 | 50ms | 100ms | Baseline |
| L1 - Connection Pooling | 150-300 | 75-150 | 40ms | 80ms | +50% throughput |
| L2 - Read Cache | 800-1500 | 50-100 | 5ms | 100ms | 5-10x read improvement |
| L3 - Read Replicas | 400-800 | 50-100 | 15ms | 100ms | 2-4x read scaling |
| L4 - DB Sharding | 300-600 | 150-300 | 20ms | 60ms | 2-3x write scaling |
| L5 - Multi-Tier Cache | 2000-5000 | 50-100 | 1ms | 100ms | 10-20x read improvement |
| L6 - Write Buffering | 100-200 | 500-1000 | 50ms | 5ms | 10x write improvement |
| L7 - CQRS | 1000-2000 | 200-400 | 10ms | 30ms | Optimized both paths |
| L8 - Polyglot | 1500-3000 | 100-200 | 5ms | 50ms | Specialized per workload |
| L9 - Global Distributed | 500-1000 | 100-200 | 20ms | 50ms | Geographic latency |
| L10 - Enterprise | 3000-6000 | 400-800 | 1ms | 10ms | Full optimization |

*Note: Actual results vary based on hardware, network, and configuration*

### Cache Hit Rate Analysis

For layers with caching (L2, L5, L7, L8, L9, L10):

```bash
# Check cache statistics after load test
curl http://localhost:8005/cache-stats

# Expected output:
{
  "l1_hits": 5000,
  "l1_misses": 100,
  "l1_hit_rate": 0.98,
  "l2_hits": 95,
  "l2_misses": 5,
  "l2_hit_rate": 0.95
}
```

Good cache hit rates:
- L1 (in-memory): > 95%
- L2 (Redis): > 90%
- Overall: > 85%

## Best Practices

### 1. Warm-Up Phase

Always warm up caches before benchmarking:

```bash
# Write test data
for i in {1..100}; do
  curl -s -X POST http://localhost:8005/write \
    -H "Content-Type: application/json" \
    -d "{\"key\": \"warm_$i\", \"value\": \"value_$i\"}" > /dev/null
done

# Warm up cache
for i in {1..100}; do
  curl -s http://localhost:8005/read/warm_$i > /dev/null
done

# Now run actual benchmark
./load-test.sh -t read 5
```

### 2. Consistent Test Environment

```bash
# Stop other layers to avoid resource contention
docker-compose -f l0-single-db/docker-compose.yml down
docker-compose -f l1-connection-pooling/docker-compose.yml down
# ... etc

# Start only the layer being tested
cd l5-multi-tier-cache/
docker-compose up -d
sleep 15

# Run test
./load-test.sh 5
```

### 3. Monitor Resource Usage

```bash
# In another terminal, monitor Docker stats
docker stats

# Watch for:
# - CPU usage
# - Memory usage
# - Network I/O
```

### 4. Progressive Load Testing

Start low and gradually increase:

```bash
# Light load
./load-test.sh -n 100 -c 10 5

# Medium load
./load-test.sh -n 1000 -c 50 5

# Heavy load
./load-test.sh -n 5000 -c 100 5

# Stress test
./load-test.sh -n 10000 -c 200 5
```

### 5. Test Data Cleanup

```bash
# After testing, clean up test data if needed
# Most layers use ephemeral containers, so just restart:
docker-compose down
docker-compose up -d
```

### 6. Multiple Test Runs

Run tests multiple times and average results:

```bash
# Run test 3 times
for i in {1..3}; do
  echo "Run $i:"
  ./load-test.sh -n 1000 -c 50 5
  sleep 10
done
```

## Advanced Testing Scenarios

### Gradual Load Increase

```bash
# Test at different concurrency levels
for concurrency in 10 25 50 100 150 200; do
  echo "Testing with concurrency: $concurrency"
  ./load-test.sh -n 2000 -c $concurrency 5
  sleep 5
done
```

### Sustained Load Test

```bash
# 5-minute sustained load
./load-test.sh -z 300 -c 100 5
```

### Burst Testing

```bash
# Short bursts with high concurrency
./load-test.sh -n 10000 -c 500 -d 5 5
```

### Comparison Testing

```bash
#!/bin/bash
# Compare performance across layers

for layer in 0 2 5 10; do
  echo "Testing Layer $layer"
  ./load-test.sh -n 1000 -c 50 -t read $layer > results_l${layer}.txt
  sleep 10
done

# Compare results
grep "Requests/sec" results_l*.txt
```

## Troubleshooting

### High Error Rate

```bash
# Check service logs
docker-compose logs api

# Reduce concurrency
./load-test.sh -n 1000 -c 25 5

# Add delays between requests
./load-test.sh -r 100 5  # 100 req/sec max
```

### Timeouts

```bash
# Increase timeout in oha
oha -n 1000 -c 50 --timeout 30 \
  http://localhost:8005/read/test
```

### Connection Refused

```bash
# Verify service is running
docker-compose ps

# Check health
curl http://localhost:8005/health

# Restart service
docker-compose restart api
```

## Generating Reports

### Save Results to File

```bash
# JSON output
oha -n 1000 -c 50 --json \
  http://localhost:8005/read/test > results.json

# Custom format
./load-test.sh 5 2>&1 | tee load_test_results.log
```

### Compare Results

```bash
# Test before optimization
./load-test.sh -n 5000 -c 100 5 > before.txt

# Make changes...

# Test after optimization
./load-test.sh -n 5000 -c 100 5 > after.txt

# Compare
diff before.txt:after.txt
```

## Additional Resources

- [oha Documentation](https://github.com/hatoo/oha)
- [TESTING.md](TESTING.md) - Functional testing guide
- [LAYERS.md](LAYERS.md) - Architecture specifications
- Each layer's README - Layer-specific performance characteristics

---

**Happy Load Testing!** 🚀
