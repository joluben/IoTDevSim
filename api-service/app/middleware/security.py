"""
Security Middleware
Security headers and protection middleware
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import structlog
from typing import Dict, Optional, Set
from collections import defaultdict
import asyncio
import redis.asyncio as aioredis

from app.core.simple_config import settings, REDIS_CONFIG

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip security headers for preflight CORS requests
        if request.method == "OPTIONS":
            return await call_next(request)

        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS only in production with HTTPS
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # API versioning header
        response.headers["API-Version"] = "v1"
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with per-IP and per-user limits.
    Uses Redis (INCR + EXPIRE) so limits are shared across Gunicorn workers.
    Falls back to in-memory counting when Redis is unavailable.
    """

    _WINDOW_SECONDS = 60
    _KEY_PREFIX = "rl:"

    def __init__(self, app, calls_per_minute: int = None):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute or settings.RATE_LIMIT_PER_MINUTE
        # Redis client — lazy-initialised on first request
        self._redis: Optional[aioredis.Redis] = None
        self._redis_available: bool = True
        # In-memory fallback (used only when Redis is down)
        self._fallback: Dict[str, list] = defaultdict(list)
        self._fallback_cleanup = time.time()

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Lazy-connect to Redis; disable on persistent failure."""
        if not self._redis_available:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    REDIS_CONFIG["url"],
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True,
                )
                await self._redis.ping()
                logger.info("rate_limiter.redis_connected")
            except Exception as e:
                logger.warning("rate_limiter.redis_unavailable, using in-memory fallback", error=str(e))
                self._redis_available = False
                self._redis = None
                return None
        return self._redis

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import verify_token
                user_id = verify_token(auth_header[7:], token_type="access")
                return f"user:{user_id}"
            except Exception:
                pass

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"

        client_host = getattr(request.client, 'host', 'unknown')
        return f"ip:{client_host}"

    async def _check_redis(self, client_id: str) -> tuple[int, int]:
        """Check and increment counter in Redis. Returns (count, remaining)."""
        r = await self._get_redis()
        if r is None:
            return self._check_fallback(client_id)
        try:
            key = f"{self._KEY_PREFIX}{client_id}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, self._WINDOW_SECONDS)
            ttl = await r.ttl(key)
            remaining = max(0, self.calls_per_minute - count)
            return count, remaining
        except Exception as e:
            logger.warning("rate_limiter.redis_error, falling back to in-memory", error=str(e))
            self._redis_available = False
            self._redis = None
            return self._check_fallback(client_id)

    def _check_fallback(self, client_id: str) -> tuple[int, int]:
        """In-memory fallback rate limiting (single-worker only)."""
        now = time.time()
        # Periodic cleanup
        if now - self._fallback_cleanup > self._WINDOW_SECONDS:
            cutoff = now - self._WINDOW_SECONDS
            for cid in list(self._fallback.keys()):
                self._fallback[cid] = [t for t in self._fallback[cid] if t > cutoff]
                if not self._fallback[cid]:
                    del self._fallback[cid]
            self._fallback_cleanup = now

        self._fallback[client_id] = [
            t for t in self._fallback[client_id]
            if t > now - self._WINDOW_SECONDS
        ]
        self._fallback[client_id].append(now)
        count = len(self._fallback[client_id])
        remaining = max(0, self.calls_per_minute - count)
        return count, remaining

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for preflight CORS requests and health checks
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_id = self._get_client_id(request)
        count, remaining = await self._check_redis(client_id)

        if count > self.calls_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                requests_count=count,
                limit=self.calls_per_minute,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.calls_per_minute} requests per minute allowed",
                    "retry_after": self._WINDOW_SECONDS,
                },
                headers={"Retry-After": str(self._WINDOW_SECONDS)},
            )

        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self._WINDOW_SECONDS))

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Request validation and sanitization middleware
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.max_request_size = settings.MAX_UPLOAD_SIZE
        self.blocked_user_agents = {
            "sqlmap",
            "nikto",
            "nmap",
            "masscan",
            "nessus"
        }
    
    def _is_suspicious_request(self, request: Request) -> bool:
        """Check if request looks suspicious"""
        # Check User-Agent
        user_agent = request.headers.get("User-Agent", "").lower()
        if any(blocked in user_agent for blocked in self.blocked_user_agents):
            return True
        
        # Check for common attack patterns in URL
        suspicious_patterns = [
            "../", "..\\", "/etc/passwd", "/proc/", "cmd.exe",
            "<script", "javascript:", "vbscript:", "onload=",
            "union select", "drop table", "insert into"
        ]
        
        url_path = str(request.url.path).lower()
        query_string = str(request.url.query).lower()
        
        for pattern in suspicious_patterns:
            if pattern in url_path or pattern in query_string:
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                "Request too large",
                content_length=content_length,
                max_size=self.max_request_size,
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request too large",
                    "message": f"Maximum request size is {self.max_request_size} bytes"
                }
            )
        
        # Check for suspicious requests
        if self._is_suspicious_request(request):
            client_host = getattr(request.client, 'host', 'unknown')
            logger.warning(
                "Suspicious request blocked",
                client_ip=client_host,
                path=request.url.path,
                user_agent=request.headers.get("User-Agent", "")
            )
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Bad request",
                    "message": "Request contains invalid content"
                }
            )
        
        return await call_next(request)
