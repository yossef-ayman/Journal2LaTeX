"""Rate limiting and concurrency control for Journal2LaTeX API.

Protects resource-intensive endpoints (upload, compilation, conversion) from
Denial-of-Service (DoS) and CPU/memory exhaustion.
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


class InMemoryRateLimiter:
    """Sliding window in-memory rate limiter per IP address."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.rpm = requests_per_minute
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str, cost: int = 1) -> bool:
        """Check if request from client_ip is within the rate limit."""
        now = time.time()
        window_start = now - 60.0

        async with self._lock:
            timestamps = self._records[client_ip]
            # Prune timestamps older than 60 seconds
            valid_timestamps = [t for t in timestamps if t > window_start]
            if len(valid_timestamps) + cost > self.rpm:
                self._records[client_ip] = valid_timestamps
                return False
            valid_timestamps.extend([now] * cost)
            self._records[client_ip] = valid_timestamps
            return True

    async def cleanup(self) -> None:
        """Periodically prune stale IPs to prevent memory leaks."""
        now = time.time()
        window_start = now - 120.0
        async with self._lock:
            stale_keys = [
                ip for ip, times in self._records.items()
                if not times or times[-1] < window_start
            ]
            for ip in stale_keys:
                del self._records[ip]


# Global rate limiter instance
_global_limiter: Optional[InMemoryRateLimiter] = None
# Global compilation concurrency semaphore
_compilation_semaphore: Optional[asyncio.Semaphore] = None


def get_rate_limiter(rpm: int = 60) -> InMemoryRateLimiter:
    global _global_limiter
    if _global_limiter is None or _global_limiter.rpm != rpm:
        _global_limiter = InMemoryRateLimiter(rpm)
    return _global_limiter


def get_compilation_semaphore(max_concurrent: int = 4) -> asyncio.Semaphore:
    global _compilation_semaphore
    if _compilation_semaphore is None:
        _compilation_semaphore = asyncio.Semaphore(max_concurrent)
    return _compilation_semaphore


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Starlette middleware to limit requests per minute for sensitive endpoints."""

    def __init__(self, app, enabled: bool = True, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.limiter = get_rate_limiter(requests_per_minute)
        # Paths that are expensive and subject to stricter rate limits
        self.heavy_prefixes = ("/upload", "/compile", "/convert", "/templates/upload")

    def _get_client_ip(self, request: Request) -> str:
        # Check standard reverse proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        # Only rate limit mutating / heavy methods on relevant endpoints
        if request.method in ("POST", "PUT") and any(path.startswith(prefix) for prefix in self.heavy_prefixes):
            client_ip = self._get_client_ip(request)
            allowed = await self.limiter.is_allowed(client_ip)
            if not allowed:
                return JSONResponse(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many requests. Please wait a moment before trying again."
                    },
                    headers={"Retry-After": "60"},
                )

        return await call_next(request)
