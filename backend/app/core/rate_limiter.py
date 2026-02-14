"""
Rate limiting middleware to prevent brute force and DoS attacks.

Uses in-memory storage for simplicity. For production with multiple workers,
consider Redis or similar distributed cache.
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self, requests: int = 100, window: int = 60):
        """
        Args:
            requests: Maximum requests allowed in window
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        # Dict[client_id, List[timestamp]]
        self.clients: Dict[str, list] = defaultdict(list)
        self.last_cleanup = time.time()
    
    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if client is allowed to make request.
        
        Returns:
            (allowed: bool, remaining: int)
        """
        now = time.time()
        
        # Cleanup old entries every 5 minutes
        if now - self.last_cleanup > 300:
            self._cleanup(now)
            self.last_cleanup = now
        
        # Get client's request timestamps
        timestamps = self.clients[client_id]
        
        # Remove timestamps outside window
        cutoff = now - self.window
        timestamps = [ts for ts in timestamps if ts > cutoff]
        self.clients[client_id] = timestamps
        
        # Check if under limit
        if len(timestamps) < self.requests:
            timestamps.append(now)
            return True, self.requests - len(timestamps)
        else:
            return False, 0
    
    def _cleanup(self, now: float):
        """Remove expired entries to prevent memory bloat."""
        cutoff = now - self.window
        for client_id in list(self.clients.keys()):
            timestamps = [ts for ts in self.clients[client_id] if ts > cutoff]
            if timestamps:
                self.clients[client_id] = timestamps
            else:
                del self.clients[client_id]
        
        logger.info(f"Rate limiter cleanup: {len(self.clients)} active clients")


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests=settings.RATE_LIMIT_REQUESTS,
    window=settings.RATE_LIMIT_WINDOW_SECONDS
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # For authenticated requests, use user ID if available
        # This prevents sharing rate limit across users on same IP
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            client_id = f"user:{auth_header[7:20]}"  # Use token prefix
        else:
            client_id = f"ip:{client_ip}"
        
        # Check rate limit
        allowed, remaining = rate_limiter.is_allowed(client_id)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.method} {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {settings.RATE_LIMIT_WINDOW_SECONDS} seconds.",
                headers={
                    "Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(settings.RATE_LIMIT_WINDOW_SECONDS)
        
        return response
