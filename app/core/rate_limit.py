import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    """Allows `max_requests` per `window_seconds` for each client IP.

    It keeps the request times in memory, so it resets when the server restarts
    and does not work across several server processes. In a real production app
    you would store the counters in Redis instead.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def __call__(self, request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()

            if len(hits) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


# One limiter for buying tickets, one (stricter) for login attempts
purchase_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)
login_limiter = RateLimiter(10, 60)
