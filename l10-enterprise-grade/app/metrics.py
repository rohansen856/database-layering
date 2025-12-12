"""Prometheus metrics"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry
import time

# Create registry
registry = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    registry=registry
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_level'],
    registry=registry
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    registry=registry
)

# Database metrics
db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['shard'],
    registry=registry
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['shard'],
    registry=registry
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['service'],
    registry=registry
)

# Rate limiter metrics
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded',
    registry=registry
)

# Application metrics
active_connections = Gauge(
    'active_connections',
    'Number of active database connections',
    ['shard'],
    registry=registry
)

# Helper class for timing
class Timer:
    def __init__(self):
        self.start_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.duration = time.time() - self.start_time

def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest(registry)

def get_content_type():
    """Get metrics content type"""
    return CONTENT_TYPE_LATEST
