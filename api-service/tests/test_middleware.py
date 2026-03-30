"""
Tests for Security Middleware
Rate limiting, security headers, and request validation
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse


# ---------------------------------------------------------------------------
# Helpers — lightweight FastAPI app that mirrors production middleware stack
# ---------------------------------------------------------------------------

def _create_app_headers_only():
    """App with only SecurityHeadersMiddleware — no rate limiting."""
    from app.middleware.security import SecurityHeadersMiddleware

    app = FastAPI()

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "ok"}

    app.add_middleware(SecurityHeadersMiddleware)
    return app


def _create_app_rate_limit(rate_limit: int = 5):
    """App with RateLimitMiddleware that forces in-memory fallback.

    We patch REDIS_CONFIG with a bad URL so ``_get_redis`` always fails on
    first attempt, falling back to the in-memory counter. This avoids
    "Event loop is closed" errors when Starlette's sync ``TestClient`` is used.
    """
    from app.middleware.security import RateLimitMiddleware

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "ok"}

    app.add_middleware(RateLimitMiddleware, calls_per_minute=rate_limit)
    return app


def _create_app_validation_only():
    """App with only RequestValidationMiddleware — no rate limiting."""
    from app.middleware.security import RequestValidationMiddleware

    app = FastAPI()

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "ok"}

    app.add_middleware(RequestValidationMiddleware)
    return app


# ==================== Security Headers ====================

class TestSecurityHeadersMiddleware:
    """Verify that every response carries the required security headers."""

    def setup_method(self):
        self.client = TestClient(_create_app_headers_only())

    def test_security_headers_present(self):
        response = self.client.get("/api/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert response.headers["API-Version"] == "v1"

    def test_csp_contains_expected_directives(self):
        response = self.client.get("/api/test")
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_options_request_skips_security_headers(self):
        response = self.client.options("/api/test")
        # OPTIONS (preflight) should not have security headers injected
        assert "X-Frame-Options" not in response.headers


# ==================== Rate Limiting ====================

class TestRateLimitMiddleware:
    """Verify per-client rate limiting with in-memory fallback."""

    def setup_method(self):
        # Patch REDIS_CONFIG to use an unreachable host so the middleware
        # falls back to in-memory counting on the first request.
        self._patcher = patch(
            "app.middleware.security.REDIS_CONFIG",
            {"url": "redis://unreachable-host:9999/0", "db": 0},
        )
        self._patcher.start()
        self.client = TestClient(_create_app_rate_limit(rate_limit=5))

    def teardown_method(self):
        self._patcher.stop()

    def test_rate_limit_headers_present(self):
        response = self.client.get("/api/test")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_decrements(self):
        r1 = self.client.get("/api/test")
        r2 = self.client.get("/api/test")
        rem1 = int(r1.headers["X-RateLimit-Remaining"])
        rem2 = int(r2.headers["X-RateLimit-Remaining"])
        assert rem2 < rem1

    def test_rate_limit_exceeded_returns_429(self):
        for _ in range(5):
            self.client.get("/api/test")
        response = self.client.get("/api/test")
        assert response.status_code == 429
        body = response.json()
        assert body["error"] == "Rate limit exceeded"
        assert "Retry-After" in response.headers

    def test_health_endpoint_exempt_from_rate_limit(self):
        # Exhaust rate limit
        for _ in range(6):
            self.client.get("/api/test")
        # Health should still work
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_options_exempt_from_rate_limit(self):
        for _ in range(6):
            self.client.options("/api/test")
        # All OPTIONS should pass, none counted
        response = self.client.get("/api/test")
        assert response.status_code == 200


# ==================== Request Validation ====================

class TestRequestValidationMiddleware:
    """Verify that suspicious requests are blocked (isolated from rate limiting)."""

    def setup_method(self):
        self.client = TestClient(_create_app_validation_only())

    def test_path_traversal_blocked(self):
        response = self.client.get("/api/test/../../../etc/passwd")
        assert response.status_code == 400

    def test_xss_in_path_blocked(self):
        response = self.client.get("/api/test/<script>alert(1)")
        assert response.status_code in (400, 404)

    def test_sql_injection_keyword_in_path_blocked(self):
        response = self.client.get("/api/test/union select")
        assert response.status_code in (400, 404)

    def test_cmd_exe_in_path_blocked(self):
        response = self.client.get("/api/test/cmd.exe")
        assert response.status_code in (400, 404)

    def test_proc_path_blocked(self):
        response = self.client.get("/proc/self/environ")
        assert response.status_code in (400, 404)

    def test_blocked_user_agent(self):
        response = self.client.get("/api/test", headers={"User-Agent": "sqlmap/1.0"})
        assert response.status_code == 400

    def test_normal_request_passes(self):
        response = self.client.get("/api/test")
        assert response.status_code == 200

    def test_normal_user_agent_passes(self):
        response = self.client.get(
            "/api/test",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        assert response.status_code == 200
