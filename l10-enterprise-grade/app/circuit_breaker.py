"""Circuit Breaker pattern implementation"""
import time
from enum import Enum
from threading import Lock
from app.config import settings

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = None, timeout: int = None):
        self.name = name
        self.failure_threshold = failure_threshold or settings.circuit_breaker_threshold
        self.timeout = timeout or settings.circuit_breaker_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = Lock()

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.failure_count = 0
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def _should_attempt_reset(self):
        """Check if enough time has passed to attempt reset"""
        return (time.time() - self.last_failure_time) >= self.timeout

    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value

    def reset(self):
        """Manually reset circuit breaker"""
        with self.lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = CircuitState.CLOSED

# Global circuit breakers for different services
circuit_breakers = {
    "shard1": CircuitBreaker("shard1"),
    "shard2": CircuitBreaker("shard2"),
    "cache_l1": CircuitBreaker("cache_l1"),
    "cache_l2": CircuitBreaker("cache_l2")
}

def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create circuit breaker"""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name)
    return circuit_breakers[name]

def get_all_states() -> dict:
    """Get states of all circuit breakers"""
    return {name: cb.get_state() for name, cb in circuit_breakers.items()}
