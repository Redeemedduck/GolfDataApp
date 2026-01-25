"""
Rate Limiter for Uneekor API and Portal Access.

Implements a token bucket algorithm with:
- Conservative defaults (6 requests/minute)
- Random jitter to appear more natural
- Async support for non-blocking waits
- Request logging for debugging

Conservative Rate Limiting Explained:
- Uneekor likely has rate limits, but they're not documented
- Being conservative (6 req/min vs aggressive 60 req/min) means:
  - Less likely to get IP blocked
  - Less load on Uneekor servers
  - Backfill takes longer but is more reliable
  - Production automation is sustainable long-term
"""

import time
import random
import asyncio
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from collections import deque


@dataclass
class RequestLog:
    """Record of a rate-limited request."""
    timestamp: datetime
    wait_time: float
    request_type: str


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""
    requests_per_minute: int = 6          # Conservative: 6 requests per minute
    burst_size: int = 2                   # Allow small burst
    min_delay_seconds: float = 8.0        # Minimum 8 seconds between requests
    max_jitter_seconds: float = 4.0       # Add up to 4 seconds random delay
    backoff_multiplier: float = 2.0       # Exponential backoff multiplier
    max_backoff_seconds: float = 300.0    # Max 5 minute backoff


class RateLimiter:
    """
    Token bucket rate limiter with jitter for natural request patterns.

    Usage:
        limiter = RateLimiter()

        # Synchronous usage
        limiter.wait()  # Blocks until request allowed
        make_request()

        # Async usage
        await limiter.wait_async()
        await make_request_async()

        # Check without waiting
        if limiter.can_proceed():
            make_request()

    Understanding Rate Limiting:
        Rate limiting controls how fast you make requests to a server.
        Think of it like a queue at a coffee shop:

        - requests_per_minute: How many customers served per minute
        - burst_size: How many can order at once during slow periods
        - jitter: Random small delays so requests don't look automated

        Why conservative (6/min vs 60/min)?
        - Uneekor is a small company, likely modest server capacity
        - No published rate limits = we should be extra careful
        - Getting blocked = no data at all
        - Slow and steady wins the race for historical backfill
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limiter configuration (uses conservative defaults if None)
        """
        self.config = config or RateLimiterConfig()

        # Token bucket state
        self.tokens = float(self.config.burst_size)
        self.last_update = time.monotonic()

        # Calculate token refill rate (tokens per second)
        self.refill_rate = self.config.requests_per_minute / 60.0

        # Track last request time for minimum delay
        self.last_request_time: Optional[float] = None

        # Request history for debugging
        self.request_log: deque = deque(maxlen=100)

        # Backoff state for errors
        self.consecutive_errors = 0
        self.current_backoff = 0.0

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(
            self.config.burst_size,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_update = now

    def _calculate_wait_time(self) -> float:
        """Calculate how long to wait before next request."""
        self._refill_tokens()

        wait_time = 0.0

        # Check if we have tokens available
        if self.tokens < 1.0:
            # Calculate time to get one token
            tokens_needed = 1.0 - self.tokens
            wait_time = tokens_needed / self.refill_rate

        # Enforce minimum delay since last request
        if self.last_request_time is not None:
            elapsed_since_last = time.monotonic() - self.last_request_time
            min_delay_remaining = self.config.min_delay_seconds - elapsed_since_last
            if min_delay_remaining > 0:
                wait_time = max(wait_time, min_delay_remaining)

        # Add backoff if we've had errors
        if self.current_backoff > 0:
            wait_time = max(wait_time, self.current_backoff)

        # Add jitter for natural timing
        jitter = random.uniform(0, self.config.max_jitter_seconds)
        wait_time += jitter

        return wait_time

    def can_proceed(self) -> bool:
        """
        Check if a request can proceed immediately without waiting.

        Returns:
            True if request can proceed now
        """
        self._refill_tokens()

        if self.tokens < 1.0:
            return False

        if self.last_request_time is not None:
            elapsed = time.monotonic() - self.last_request_time
            if elapsed < self.config.min_delay_seconds:
                return False

        return True

    def wait(self, request_type: str = 'generic') -> float:
        """
        Wait until a request is allowed (blocking).

        Args:
            request_type: Label for logging purposes

        Returns:
            Actual wait time in seconds
        """
        wait_time = self._calculate_wait_time()

        if wait_time > 0:
            time.sleep(wait_time)

        # Consume a token
        self._refill_tokens()
        self.tokens -= 1.0
        self.last_request_time = time.monotonic()

        # Log the request
        self.request_log.append(RequestLog(
            timestamp=datetime.utcnow(),
            wait_time=wait_time,
            request_type=request_type
        ))

        return wait_time

    async def wait_async(self, request_type: str = 'generic') -> float:
        """
        Wait until a request is allowed (non-blocking async).

        Args:
            request_type: Label for logging purposes

        Returns:
            Actual wait time in seconds
        """
        wait_time = self._calculate_wait_time()

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # Consume a token
        self._refill_tokens()
        self.tokens -= 1.0
        self.last_request_time = time.monotonic()

        # Log the request
        self.request_log.append(RequestLog(
            timestamp=datetime.utcnow(),
            wait_time=wait_time,
            request_type=request_type
        ))

        return wait_time

    def report_success(self) -> None:
        """Report a successful request to reset backoff."""
        self.consecutive_errors = 0
        self.current_backoff = 0.0

    def report_error(self) -> float:
        """
        Report a failed request to increase backoff.

        Returns:
            Current backoff time in seconds
        """
        self.consecutive_errors += 1

        # Calculate exponential backoff
        self.current_backoff = min(
            self.config.min_delay_seconds * (self.config.backoff_multiplier ** self.consecutive_errors),
            self.config.max_backoff_seconds
        )

        return self.current_backoff

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dict with current state and recent history
        """
        self._refill_tokens()

        recent_requests = list(self.request_log)[-10:]
        avg_wait = sum(r.wait_time for r in recent_requests) / len(recent_requests) if recent_requests else 0

        return {
            'tokens_available': self.tokens,
            'requests_per_minute': self.config.requests_per_minute,
            'min_delay_seconds': self.config.min_delay_seconds,
            'consecutive_errors': self.consecutive_errors,
            'current_backoff': self.current_backoff,
            'total_requests': len(self.request_log),
            'recent_avg_wait': avg_wait,
        }

    def estimate_time_for_requests(self, num_requests: int) -> float:
        """
        Estimate total time to complete a number of requests.

        Args:
            num_requests: Number of requests to estimate

        Returns:
            Estimated time in seconds

        Example:
            limiter = RateLimiter()  # 6 req/min default
            time_for_100 = limiter.estimate_time_for_requests(100)
            # Returns ~1000 seconds (16.7 minutes) at 6 req/min
        """
        if num_requests <= 0:
            return 0.0

        # Base time from rate limit
        base_time = num_requests / self.refill_rate

        # Add minimum delays
        delay_time = num_requests * self.config.min_delay_seconds

        # Add average jitter
        avg_jitter = self.config.max_jitter_seconds / 2
        jitter_time = num_requests * avg_jitter

        # Use the larger of rate-limited time or delay time
        return max(base_time, delay_time) + jitter_time


# Pre-configured rate limiters for different use cases
def get_conservative_limiter() -> RateLimiter:
    """
    Get a conservative rate limiter for production use.

    6 requests/minute, good for automated daily syncs.
    """
    return RateLimiter(RateLimiterConfig(
        requests_per_minute=6,
        burst_size=2,
        min_delay_seconds=8.0,
        max_jitter_seconds=4.0,
    ))


def get_backfill_limiter() -> RateLimiter:
    """
    Get a rate limiter for historical backfill.

    10 requests/minute, slightly faster for catching up on old data.
    Still conservative enough to avoid rate limiting.
    """
    return RateLimiter(RateLimiterConfig(
        requests_per_minute=10,
        burst_size=3,
        min_delay_seconds=5.0,
        max_jitter_seconds=3.0,
    ))


def get_aggressive_limiter() -> RateLimiter:
    """
    Get a more aggressive rate limiter.

    WARNING: Use only for testing or if you're confident in Uneekor's capacity.
    20 requests/minute with shorter delays.
    """
    return RateLimiter(RateLimiterConfig(
        requests_per_minute=20,
        burst_size=5,
        min_delay_seconds=2.0,
        max_jitter_seconds=2.0,
    ))
