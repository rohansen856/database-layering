"""Rate Limiter using Redis sliding window"""
import redis
import time
from app.config import settings

rate_limiter_client = None

def init_rate_limiter():
    """Initialize rate limiter Redis client"""
    global rate_limiter_client
    rate_limiter_client = redis.from_url(settings.rate_limiter_url, decode_responses=True)
    rate_limiter_client.ping()
    print("Rate limiter initialized")

def close_rate_limiter():
    """Close rate limiter client"""
    global rate_limiter_client
    if rate_limiter_client:
        rate_limiter_client.close()

def is_rate_limited(client_id: str) -> tuple[bool, int, int]:
    """
    Check if client is rate limited using sliding window algorithm
    Returns: (is_limited, remaining_requests, reset_in_seconds)
    """
    if not rate_limiter_client:
        return (False, settings.rate_limit_requests, 0)

    key = f"rate_limit:{client_id}"
    current_time = int(time.time())
    window_start = current_time - settings.rate_limit_window

    try:
        # Remove old entries outside the window
        rate_limiter_client.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        request_count = rate_limiter_client.zcard(key)

        if request_count >= settings.rate_limit_requests:
            # Get the oldest request in window
            oldest = rate_limiter_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                reset_time = int(oldest[0][1]) + settings.rate_limit_window
                reset_in = max(0, reset_time - current_time)
                return (True, 0, reset_in)

        # Add current request
        rate_limiter_client.zadd(key, {str(current_time): current_time})
        rate_limiter_client.expire(key, settings.rate_limit_window)

        remaining = settings.rate_limit_requests - request_count - 1
        return (False, remaining, settings.rate_limit_window)

    except Exception as e:
        print(f"Rate limiter error: {e}")
        # Fail open - allow request if rate limiter fails
        return (False, settings.rate_limit_requests, 0)

def reset_rate_limit(client_id: str):
    """Reset rate limit for a client"""
    if rate_limiter_client:
        key = f"rate_limit:{client_id}"
        rate_limiter_client.delete(key)
