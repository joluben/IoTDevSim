"""HTTP/HTTPS protocol handler (KISS).

Design goals:
- Deterministic test: single request (or connection attempt) with timeout.
- No pooling, no circuit-breaker, no retry manager.
- Keep public contract used by ConnectionTestingService.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict

import httpx
import structlog

from app.schemas.connection import HTTPConfig, HTTPAuthType

from .base import ConnectionTestResult, ProtocolHandler

logger = structlog.get_logger()


class HTTPHandler(ProtocolHandler):
    """Handler for HTTP/HTTPS protocol connection testing (KISS)."""

    def __init__(self):
        super().__init__("HTTP/HTTPS")

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        try:
            HTTPConfig(**config)
            return True
        except Exception:
            return False

    async def test_connection(self, config: Dict[str, Any], timeout: int = 10) -> ConnectionTestResult:
        start_time = time.perf_counter()
        timestamp = datetime.utcnow()

        try:
            http_config = HTTPConfig(**config)

            headers: Dict[str, str] = dict(http_config.headers or {})

            auth: httpx.Auth | None = None
            if http_config.auth_type == HTTPAuthType.BASIC:
                auth = (http_config.username or "", http_config.password or "")
            elif http_config.auth_type == HTTPAuthType.BEARER:
                if http_config.bearer_token:
                    headers["Authorization"] = f"Bearer {http_config.bearer_token}"
            elif http_config.auth_type == HTTPAuthType.API_KEY:
                if http_config.api_key_header and http_config.api_key_value:
                    headers[http_config.api_key_header] = http_config.api_key_value

            client_timeout = httpx.Timeout(
                connect=timeout,
                read=timeout,
                write=timeout,
                pool=timeout,
            )

            async with httpx.AsyncClient(
                timeout=client_timeout,
                verify=http_config.verify_ssl,
                follow_redirects=True,
            ) as client:
                # KISS: send the configured method without payload.
                # For many webhook endpoints this may return 405, which still proves connectivity.
                response = await client.request(
                    method=http_config.method.value,
                    url=http_config.endpoint_url,
                    headers=headers,
                    auth=auth,
                )

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Connectivity criteria (KISS): request succeeded at network level.
            # We do not fail on non-2xx because many endpoints restrict methods.
            return ConnectionTestResult(
                success=True,
                message="HTTP connectivity successful",
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={
                    "protocol": "http",
                    "endpoint_url": http_config.endpoint_url,
                    "method": http_config.method.value,
                    "status_code": response.status_code,
                    "verify_ssl": http_config.verify_ssl,
                },
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ConnectionTestResult(
                success=False,
                message=self._sanitize_error_message(e),
                duration_ms=duration_ms,
                timestamp=timestamp,
                details={"protocol": "http"},
                error_code=self._get_error_code(e),
            )
