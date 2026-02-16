"""
Security Middleware
Security headers and protection middleware
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import structlog
from typing import Dict, Set
from collections import defaultdict
import asyncio

from app.core.simple_config import settings

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
    Rate limiting middleware with per-IP and per-user limits
    """
    
    def __init__(self, app, calls_per_minute: int = None):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every minute
        self.last_cleanup = time.time()
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from token if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import verify_token
                user_id = verify_token(auth_header[7:], token_type="access")
                return f"user:{user_id}"
            except:
                pass
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_host = getattr(request.client, 'host', 'unknown')
        return f"ip:{client_host}"
    
    def _cleanup_old_requests(self):
        """Clean up old request records"""
        current_time = time.time()
        cutoff_time = current_time - 60  # Keep only last minute
        
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff_time
            ]
            
            # Remove empty entries
            if not self.requests[client_id]:
                del self.requests[client_id]
        
        self.last_cleanup = current_time
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for preflight CORS requests and health checks
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        current_time = time.time()
        
        # Periodic cleanup
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests()
        
        client_id = self._get_client_id(request)
        
        # Check rate limit
        client_requests = self.requests[client_id]
        recent_requests = [
            req_time for req_time in client_requests
            if req_time > current_time - 60
        ]
        
        if len(recent_requests) >= self.calls_per_minute:
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                requests_count=len(recent_requests),
                limit=self.calls_per_minute,
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.calls_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self.requests[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.calls_per_minute - len(recent_requests) - 1)
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
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
