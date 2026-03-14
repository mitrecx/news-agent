"""Security middleware for the FastAPI application.

This module provides rate limiting, CORS configuration, and security headers
to protect the API from common web vulnerabilities.
"""

import time
import logging
from typing import Callable
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import hashlib
import ipaddress

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm.

    Tracks requests per IP address and enforces rate limits.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # Track requests: {ip: [(timestamp, count), ...]}
        self.minute_window: defaultdict[str, list[tuple[float, int]]] = defaultdict(list)
        self.hour_window: defaultdict[str, list[tuple[float, int]]] = defaultdict(list)
        self._cleanup_threshold = 3600  # Cleanup old data every hour

    def _cleanup_old_entries(
        self,
        window: defaultdict[str, list[tuple[float, int]]],
        cutoff_time: float
    ) -> None:
        """Remove entries older than cutoff_time."""
        current_time = time.time()
        if current_time - cutoff_time > self._cleanup_threshold:
            for ip in list(window.keys()):
                # Filter out old entries
                window[ip] = [
                    (ts, count) for ts, count in window[ip]
                    if current_time - ts < self._cleanup_threshold
                ]
                # Remove IP if no entries left
                if not window[ip]:
                    del window[ip]

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.

        Uses X-Forwarded-For header if available (for proxied requests),
        otherwise falls back to client IP address.
        """
        # Check for X-Forwarded-For header (for reverse proxy setups)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            ip = forwarded_for.split(",")[0].strip()
        else:
            # Fall back to direct client IP
            ip = request.client.host if request.client else "unknown"

        # Hash IP for privacy (GDPR compliance)
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    def is_allowed(self, request: Request) -> tuple[bool, str]:
        """
        Check if request is within rate limits.

        Args:
            request: The incoming request

        Returns:
            Tuple of (is_allowed, error_message)
        """
        client_id = self._get_client_identifier(request)
        current_time = time.time()

        # Check minute limit
        self._cleanup_old_entries(self.minute_window, current_time - 60)
        self.minute_window[client_id] = [
            (ts, count) for ts, count in self.minute_window[client_id]
            if current_time - ts < 60
        ]

        minute_count = sum(count for _, count in self.minute_window[client_id])
        if minute_count >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {minute_count} requests per minute"

        # Check hour limit
        self._cleanup_old_entries(self.hour_window, current_time - 3600)
        self.hour_window[client_id] = [
            (ts, count) for ts, count in self.hour_window[client_id]
            if current_time - ts < 3600
        ]

        hour_count = sum(count for _, count in self.hour_window[client_id])
        if hour_count >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {hour_count} requests per hour"

        # Record this request
        self.minute_window[client_id].append((current_time, 1))
        self.hour_window[client_id].append((current_time, 1))

        return True, ""


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for adding security headers and rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter | None = None,
        enable_rate_limit: bool = True
    ):
        """
        Initialize security middleware.

        Args:
            app: The ASGI application
            rate_limiter: Optional rate limiter instance
            enable_rate_limit: Whether to enable rate limiting
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.enable_rate_limit = enable_rate_limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through security middleware.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            The response with security headers added
        """
        # Rate limiting check
        if self.enable_rate_limit and request.url.path.startswith("/api"):
            allowed, error_msg = self.rate_limiter.is_allowed(request)
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for client: "
                    f"{request.client.host if request.client else 'unknown'}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_msg,
                    headers={"Retry-After": "60"}
                )

        # Process request
        response = await call_next(request)

        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

        for header, value in security_headers.items():
            response.headers[header] = value

        return response


def setup_cors(app) -> None:
    """
    Configure CORS middleware for the application.

    Args:
        app: The FastAPI application
    """
    allowed_origins = [
        "http://localhost:6173",  # Vue dev server
        "http://localhost:8000",  # API server
        "http://127.0.0.1:6173",
        "http://127.0.0.1:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    logger.info(f"✓ CORS configured for origins: {allowed_origins}")


def setup_security_middleware(
    app,
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    enable_rate_limit: bool = True
) -> None:
    """
    Setup security middleware for the application.

    Args:
        app: The FastAPI application
        requests_per_minute: Max requests per minute per IP
        requests_per_hour: Max requests per hour per IP
        enable_rate_limit: Whether to enable rate limiting
    """
    rate_limiter = RateLimiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour
    )

    app.add_middleware(
        SecurityMiddleware,
        rate_limiter=rate_limiter,
        enable_rate_limit=enable_rate_limit
    )

    logger.info(
        f"✓ Security middleware configured "
        f"(rate limit: {requests_per_minute}/min, {requests_per_hour}/hour)"
    )
