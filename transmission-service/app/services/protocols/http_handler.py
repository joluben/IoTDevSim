"""
HTTP/HTTPS Protocol Handler for Transmission Service
Supports POST requests to webhooks with configurable headers and auth
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

from .base import ProtocolHandler, PublishResult

logger = structlog.get_logger()


class HTTPHandler(ProtocolHandler):
    """Handler for HTTP/HTTPS webhook transmission"""
    
    def __init__(self):
        super().__init__("HTTP")
    
    async def publish(
        self,
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """POST payload to HTTP endpoint"""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Build URL (topic can be full URL or path)
            # Support both 'url' (legacy) and 'endpoint_url' (current schema)
            base_url = config.get("endpoint_url") or config.get("url", "")
            if topic.startswith("http"):
                url = topic
            elif base_url:
                # Combine base URL with topic path
                url = base_url.rstrip("/") + "/" + topic.lstrip("/")
            else:
                url = topic
            
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL: {url}")
            
            # Build headers
            headers = config.get("headers", {})
            headers.setdefault("Content-Type", "application/json")
            
            # Build auth
            auth = None
            username = config.get("username")
            password = config.get("password")
            if username and password:
                auth = (username, password)
            
            # Get method (default POST)
            method = config.get("method", "POST").upper()
            
            # SSL verification
            verify_ssl = config.get("verify_ssl", True)
            
            # Make request
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout),
                verify=verify_ssl
            ) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, auth=auth)
                elif method == "PUT":
                    response = await client.put(url, json=payload, headers=headers, auth=auth)
                elif method == "PATCH":
                    response = await client.patch(url, json=payload, headers=headers, auth=auth)
                else:  # POST default
                    response = await client.post(url, json=payload, headers=headers, auth=auth)
                
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                if response.status_code < 400:
                    return PublishResult(
                        success=True,
                        message=f"HTTP {response.status_code}",
                        latency_ms=latency_ms,
                        timestamp=timestamp,
                        details={
                            "protocol": "http",
                            "url": url,
                            "method": method,
                            "status_code": response.status_code,
                            "response_preview": response.text[:200] if response.text else None
                        }
                    )
                else:
                    return PublishResult(
                        success=False,
                        message=f"HTTP error {response.status_code}",
                        latency_ms=latency_ms,
                        timestamp=timestamp,
                        error_code=f"HTTP_{response.status_code}",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "response": response.text[:500]
                        }
                    )
                    
        except httpx.TimeoutException as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return PublishResult(
                success=False,
                message="Request timed out",
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code="TIMEOUT",
                details={"exception": str(e)}
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            self.logger.warning("HTTP publish failed", error=str(e))
            
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code,
                details={"exception": str(e)}
            )
    
    async def publish_pooled(
        self,
        pooled_client: "httpx.AsyncClient",
        config: Dict[str, Any],
        topic: str,
        payload: Dict[str, Any],
        timeout: int = 30
    ) -> PublishResult:
        """POST payload using a persistent pooled httpx.AsyncClient."""
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)

        try:
            # Support both 'endpoint_url' (current schema) and 'url' (legacy)
            base_url = config.get("endpoint_url") or config.get("url", "")
            if topic.startswith("http"):
                url = topic
            elif base_url:
                url = base_url.rstrip("/") + "/" + topic.lstrip("/")
            else:
                url = topic

            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid URL: {url}")

            headers = config.get("headers", {})
            headers.setdefault("Content-Type", "application/json")

            auth = None
            username = config.get("username")
            password = config.get("password")
            if username and password:
                auth = (username, password)

            method = config.get("method", "POST").upper()

            if method == "GET":
                response = await pooled_client.get(url, headers=headers, auth=auth)
            elif method == "PUT":
                response = await pooled_client.put(url, json=payload, headers=headers, auth=auth)
            elif method == "PATCH":
                response = await pooled_client.patch(url, json=payload, headers=headers, auth=auth)
            else:
                response = await pooled_client.post(url, json=payload, headers=headers, auth=auth)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code < 400:
                return PublishResult(
                    success=True,
                    message=f"HTTP {response.status_code}",
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    details={
                        "protocol": "http",
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] if response.text else None,
                        "pooled": True,
                    }
                )
            else:
                return PublishResult(
                    success=False,
                    message=f"HTTP error {response.status_code}",
                    latency_ms=latency_ms,
                    timestamp=timestamp,
                    error_code=f"HTTP_{response.status_code}",
                    details={
                        "url": url,
                        "status_code": response.status_code,
                        "response": response.text[:500],
                        "pooled": True,
                    }
                )

        except httpx.TimeoutException as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return PublishResult(
                success=False,
                message="Request timed out",
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code="TIMEOUT",
                details={"exception": str(e), "pooled": True}
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            error_msg = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            self.logger.warning("HTTP pooled publish failed", error=str(e))
            return PublishResult(
                success=False,
                message=error_msg,
                latency_ms=latency_ms,
                timestamp=timestamp,
                error_code=error_code,
                details={"exception": str(e), "pooled": True}
            )

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate HTTP configuration"""
        # Support both 'endpoint_url' (current schema) and 'url' (legacy)
        url = config.get("endpoint_url") or config.get("url", "")
        if not url:
            return False
        
        # URL must be http or https
        if not url.startswith(("http://", "https://")):
            return False
        
        return True
