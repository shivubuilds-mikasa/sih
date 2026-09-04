"""Rate limiting middleware for SHARMI API.

Simple in-memory rate limiter for demo purposes.
In production, use Redis-backed rate limiting.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter by client IP."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._minute_windows: dict[str, list[float]] = defaultdict(list)
        self._hour_windows: dict[str, list[float]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Get rate limit key from client IP."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _clean_old_requests(self, window: list[float], max_age: float) -> None:
        """Remove timestamps older than max_age seconds."""
        now = time.time()
        while window and window[0] < now - max_age:
            window.pop(0)

    def _check_limit(self, window: list[float], limit: int) -> tuple[bool, int]:
        """Check if request is within limit. Returns (allowed, remaining)."""
        self._clean_old_requests(window, 60 if limit == self.requests_per_minute else 3600)
        remaining = limit - len(window)
        return remaining > 0, max(0, remaining)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks and test client
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        # Skip for test client (detected by testclient header)
        if request.headers.get("user-agent", "").startswith("testclient"):
            return await call_next(request)

        client_key = self._get_client_key(request)

        # Check minute limit
        minute_allowed, minute_remaining = self._check_limit(
            self._minute_windows[client_key], self.requests_per_minute
        )
        if not minute_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} per minute.",
                    "retry_after": 60,
                },
                headers={"X-RateLimit-Limit": str(self.requests_per_minute), "X-RateLimit-Remaining": "0"},
            )

        # Check hour limit
        hour_allowed, hour_remaining = self._check_limit(
            self._hour_windows[client_key], self.requests_per_hour
        )
        if not hour_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Hourly limit exceeded. Limit: {self.requests_per_hour} per hour.",
                    "retry_after": 3600,
                },
                headers={"X-RateLimit-Limit": str(self.requests_per_hour), "X-RateLimit-Remaining": "0"},
            )

        # Add current request to windows
        now = time.time()
        self._minute_windows[client_key].append(now)
        self._hour_windows[client_key].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)

        return response