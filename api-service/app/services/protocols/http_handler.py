"""
HTTP/HTTPS Protocol Handler
Connection testing and validation for HTTP/HTTPS protocols with advanced features
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx
import threading
from urllib.parse import urlparse

from .base import ProtocolHandler, ConnectionTestResult
from .circuit_breaker import CircuitBreakerConfig, circuit_breaker_manager
from .retry_logic import retry_manager, RetryExhaustedException
from app.schemas.connection import HTTPConfig, HTTPAuthType, HTTPMethod
import structlog

logger = structlog.get_logger()


@dataclass
class HTTPSessionInfo:
    """Information about an HTTP session"""
    client: httpx.AsyncClient
    config_hash: str
    created_at: datetime
    last_used: datetime
    request_count: int = 0


class HTTPSessionManager:
    """
    Session manager for HTTP clients with connection reuse and pooling
    """
    
    def __init__(self, max_sessions: int = 10, session_timeout: int = 300):
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout  # seconds
        self._sessions: Dict[str, HTTPSessionInfo] = {}
        self._lock = threading.Lock()
        self.logger = logger.bind(component="http_session_manager")
    
    def _get_session_key(self, config: HTTPConfig) -> str:
        """Generate a unique key for session pooling"""
        from urllib.parse import urlparse
        parsed = urlparse(config.endpoint_url)
        # Create a hash based on connection-relevant config
        key_parts = [
            parsed.netloc,
            parsed.scheme,
            str(config.timeout),
            str(config.verify_ssl),
            config.auth_type.value,
            config.username or "",
        ]
        return "|".join(key_parts)
    
    async def get_session(self, config: HTTPConfig) -> httpx.AsyncClient:
        """
        Get or create an HTTP session from the pool
        
        Args:
            config: HTTP configuration
        
        Returns:
            HTTP client session
        """
        session_key = self._get_session_key(config)
        
        with self._lock:
            # Clean up expired sessions
            self._cleanup_expired_sessions()
            
            # Check if we have an existing session
            if session_key in self._sessions:
                session_info = self._sessions[session_key]
                session_info.last_used = datetime.utcnow()
                session_info.request_count += 1
                
                # Check if session is still valid
                if not session_info.client.is_closed:
                    self.logger.debug("Reusing existing HTTP session", key=session_key)
                    return session_info.client
                else:
                    # Session is closed, remove it
                    self.logger.info("Removing closed HTTP session", key=session_key)
                    del self._sessions[session_key]
            
            # Create new session
            return await self._create_session(config, session_key)
    
    async def _create_session(self, config: HTTPConfig, session_key: str) -> httpx.AsyncClient:
        """Create a new HTTP session"""
        # Clean up old sessions if we're at the limit
        if len(self._sessions) >= self.max_sessions:
            await self._cleanup_oldest_session()
        
        # Prepare session configuration
        client_config = {
            "timeout": httpx.Timeout(
                connect=config.timeout,
                read=config.timeout,
                write=config.timeout,
                pool=config.timeout
            ),
            "verify": config.verify_ssl,
            "follow_redirects": True,
            "limits": httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        }
        
        # Create the client
        client = httpx.AsyncClient(**client_config)
        
        # Store session info
        session_info = HTTPSessionInfo(
            client=client,
            config_hash=session_key,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow(),
            request_count=1
        )
        
        self._sessions[session_key] = session_info
        
        self.logger.info("Created new HTTP session", key=session_key)
        return client
    
    def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, session_info in self._sessions.items():
            age = (now - session_info.last_used).total_seconds()
            if age > self.session_timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.logger.info("Cleaning up expired HTTP session", key=key)
            asyncio.create_task(self._close_session(key))
    
    async def _cleanup_oldest_session(self):
        """Clean up the oldest unused session"""
        if not self._sessions:
            return
        
        oldest_key = min(
            self._sessions.keys(),
            key=lambda k: self._sessions[k].last_used
        )
        
        self.logger.info("Cleaning up oldest HTTP session", key=oldest_key)
        await self._close_session(oldest_key)
    
    async def _close_session(self, session_key: str):
        """Close a specific session"""
        if session_key in self._sessions:
            session_info = self._sessions[session_key]
            try:
                await session_info.client.aclose()
            except Exception as e:
                self.logger.warning("Error closing HTTP session", error=str(e))
            
            del self._sessions[session_key]
    
    async def cleanup_all(self):
        """Clean up all sessions"""
        with self._lock:
            for key in list(self._sessions.keys()):
                await self._close_session(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "max_sessions": self.max_sessions,
                "session_timeout": self.session_timeout,
                "sessions": {
                    key: {
                        "created_at": info.created_at.isoformat(),
                        "last_used": info.last_used.isoformat(),
                        "request_count": info.request_count,
                        "is_closed": info.client.is_closed
                    }
                    for key, info in self._sessions.items()
                }
            }


class HTTPHandler(ProtocolHandler):
    """Handler for HTTP/HTTPS protocol connection testing with advanced features"""
    
    def __init__(self):
        super().__init__("HTTP/HTTPS")
        self._session_manager = HTTPSessionManager()
        
        # Set up circuit breaker
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=3,
            timeout=30.0,  # Longer timeout for HTTP
            expected_exceptions=(
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
                ConnectionError,
                TimeoutError
            )
        )
        self._circuit_breaker = circuit_breaker_manager.get_breaker(
            "http_handler",
            circuit_config
        )
    
    async def test_connection(
        self,
        config: Dict[str, Any],
        timeout: int = 10
    ) -> ConnectionTestResult:
        """
        Test HTTP/HTTPS connection with comprehensive validation using circuit breaker
        
        Args:
            config: HTTP configuration dictionary
            timeout: Test timeout in seconds
        
        Returns:
            ConnectionTestResult with test outcome
        """
        start_time = time.time()
        
        try:
            # Validate configuration first
            http_config = HTTPConfig(**config)
            
            # Create test result details
            details = {
                "endpoint_url": http_config.endpoint_url,
                "method": http_config.method.value,
                "auth_type": http_config.auth_type.value,
                "timeout": http_config.timeout,
                "verify_ssl": http_config.verify_ssl,
                "headers_count": len(http_config.headers),
                "circuit_breaker_stats": self._circuit_breaker.get_stats()
            }
            
            # Perform connection test through circuit breaker
            async def test_operation():
                return await self._perform_http_test(http_config, timeout)
            
            test_result = await self._circuit_breaker.call(test_operation)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if test_result["success"]:
                return ConnectionTestResult(
                    success=True,
                    message=f"HTTP connection successful to {http_config.endpoint_url}",
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    details={**details, **test_result["details"]}
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    message=test_result["message"],
                    duration_ms=duration_ms,
                    timestamp=datetime.utcnow(),
                    details=details,
                    error_code=test_result["error_code"]
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_message = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            self.logger.error("HTTP connection test failed", error=str(e))
            
            return ConnectionTestResult(
                success=False,
                message=f"HTTP connection test failed: {error_message}",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                error_code=error_code
            )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate HTTP configuration
        
        Args:
            config: HTTP configuration to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            HTTPConfig(**config)
            return True
        except Exception as e:
            self.logger.warning("HTTP config validation failed", error=str(e))
            return False
    
    async def _perform_http_test(
        self,
        config: HTTPConfig,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Perform actual HTTP connection test using session manager
        
        Args:
            config: Validated HTTP configuration
            timeout: Test timeout in seconds
        
        Returns:
            Dictionary with test results
        """
        test_result = {"success": False, "message": "", "details": {}, "error_code": ""}
        
        try:
            # Get session from manager (with connection reuse)
            client = await self._session_manager.get_session(config)
            
            test_result["details"]["session_reused"] = True
            test_result["details"]["session_stats"] = self._session_manager.get_stats()
            
            # Prepare headers
            headers = dict(config.headers) if config.headers else {}
            
            # Add authentication headers
            auth = None
            if config.auth_type == HTTPAuthType.BASIC:
                auth = httpx.BasicAuth(config.username, config.password)
                test_result["details"]["auth_method"] = "basic"
            elif config.auth_type == HTTPAuthType.BEARER:
                headers["Authorization"] = f"Bearer {config.bearer_token}"
                test_result["details"]["auth_method"] = "bearer"
            elif config.auth_type == HTTPAuthType.API_KEY:
                headers[config.api_key_header] = config.api_key_value
                test_result["details"]["auth_method"] = "api_key"
            else:
                test_result["details"]["auth_method"] = "none"
            
            # Add content type for POST/PUT/PATCH requests
            if config.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
                if "content-type" not in [h.lower() for h in headers.keys()]:
                    headers["Content-Type"] = "application/json"
            
            # Prepare test payload for requests that support body
            test_payload = None
            if config.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
                test_payload = {
                    "test": True,
                    "timestamp": time.time(),
                    "source": "iot_devsim_connection_test"
                }
            
            # Perform the HTTP request with retry logic
            retry_handler = retry_manager.get_protocol_handler("http")
            
            async def make_request():
                request_start = time.time()
                
                if config.method == HTTPMethod.GET:
                    response = await client.get(
                        config.endpoint_url,
                        headers=headers,
                        auth=auth
                    )
                elif config.method == HTTPMethod.POST:
                    response = await client.post(
                        config.endpoint_url,
                        json=test_payload,
                        headers=headers,
                        auth=auth
                    )
                elif config.method == HTTPMethod.PUT:
                    response = await client.put(
                        config.endpoint_url,
                        json=test_payload,
                        headers=headers,
                        auth=auth
                    )
                elif config.method == HTTPMethod.PATCH:
                    response = await client.patch(
                        config.endpoint_url,
                        json=test_payload,
                        headers=headers,
                        auth=auth
                    )
                elif config.method == HTTPMethod.DELETE:
                    response = await client.delete(
                        config.endpoint_url,
                        headers=headers,
                        auth=auth
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {config.method}")
                
                request_duration = (time.time() - request_start) * 1000
                return response, request_duration
            
            try:
                response, request_duration = await retry_handler.execute(make_request)
            except RetryExhaustedException as e:
                return {
                    "success": False,
                    "message": f"HTTP request failed after retries: {e.original_exception}",
                    "error_code": self._get_error_code(e.original_exception),
                    "details": {"retry_attempts": len(e.attempts)}
                }
            
            # Analyze response
            test_result["details"].update({
                "status_code": response.status_code,
                "request_duration_ms": round(request_duration, 2),
                "response_headers_count": len(response.headers),
                "response_size_bytes": len(response.content),
                "http_version": response.http_version,
                "final_url": str(response.url)
            })
            
            # Check if response indicates success
            if 200 <= response.status_code < 300:
                test_result["success"] = True
                test_result["message"] = f"HTTP {config.method.value} request successful (status: {response.status_code})"
                
                # Try to parse response content type
                content_type = response.headers.get("content-type", "").lower()
                test_result["details"]["response_content_type"] = content_type
                
                # If JSON response, try to parse it
                if "application/json" in content_type:
                    try:
                        json_data = response.json()
                        test_result["details"]["response_json_valid"] = True
                        test_result["details"]["response_json_keys"] = list(json_data.keys()) if isinstance(json_data, dict) else []
                    except Exception:
                        test_result["details"]["response_json_valid"] = False
                
            elif 400 <= response.status_code < 500:
                # Client error - might be authentication or configuration issue
                test_result["success"] = False
                test_result["error_code"] = f"HTTP_{response.status_code}"
                
                if response.status_code == 401:
                    test_result["message"] = "HTTP request failed: Authentication required or invalid credentials"
                elif response.status_code == 403:
                    test_result["message"] = "HTTP request failed: Access forbidden"
                elif response.status_code == 404:
                    test_result["message"] = "HTTP request failed: Endpoint not found"
                else:
                    test_result["message"] = f"HTTP request failed with client error (status: {response.status_code})"
            
            elif 500 <= response.status_code < 600:
                # Server error
                test_result["success"] = False
                test_result["error_code"] = f"HTTP_{response.status_code}"
                test_result["message"] = f"HTTP request failed with server error (status: {response.status_code})"
            
            else:
                # Unexpected status code
                test_result["success"] = False
                test_result["error_code"] = f"HTTP_{response.status_code}"
                test_result["message"] = f"HTTP request returned unexpected status code: {response.status_code}"
            
            # Add response headers for debugging (sanitized)
            response_headers = dict(response.headers)
            # Remove potentially sensitive headers
            sensitive_headers = ['authorization', 'cookie', 'set-cookie', 'x-api-key']
            for header in sensitive_headers:
                if header in response_headers:
                    response_headers[header] = "[REDACTED]"
            
            test_result["details"]["response_headers"] = response_headers
            
            return test_result
            
        except Exception as e:
            error_message = self._sanitize_error_message(e)
            error_code = self._get_error_code(e)
            
            return {
                "success": False,
                "message": f"HTTP request error: {error_message}",
                "error_code": error_code,
                "details": {
                    "exception": str(e),
                    "exception_type": type(e).__name__
                }
            }
    
    async def send_request(
        self,
        config: HTTPConfig,
        method: HTTPMethod,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send an HTTP request using session manager and retry logic
        
        Args:
            config: HTTP configuration
            method: HTTP method
            endpoint: Endpoint URL
            payload: Request payload
            headers: Additional headers
        
        Returns:
            Dictionary with request results
        """
        try:
            client = await self._session_manager.get_session(config)
            
            # Prepare request headers
            request_headers = dict(config.headers) if config.headers else {}
            if headers:
                request_headers.update(headers)
            
            # Add authentication
            auth = None
            if config.auth_type == HTTPAuthType.BASIC:
                auth = httpx.BasicAuth(config.username, config.password)
            elif config.auth_type == HTTPAuthType.BEARER:
                request_headers["Authorization"] = f"Bearer {config.bearer_token}"
            elif config.auth_type == HTTPAuthType.API_KEY:
                request_headers[config.api_key_header] = config.api_key_value
            
            # Make request with retry logic
            retry_handler = retry_manager.get_protocol_handler("http")
            
            async def make_request():
                if method == HTTPMethod.GET:
                    return await client.get(endpoint, headers=request_headers, auth=auth)
                elif method == HTTPMethod.POST:
                    return await client.post(endpoint, json=payload, headers=request_headers, auth=auth)
                elif method == HTTPMethod.PUT:
                    return await client.put(endpoint, json=payload, headers=request_headers, auth=auth)
                elif method == HTTPMethod.PATCH:
                    return await client.patch(endpoint, json=payload, headers=request_headers, auth=auth)
                elif method == HTTPMethod.DELETE:
                    return await client.delete(endpoint, headers=request_headers, auth=auth)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
            
            response = await self._circuit_breaker.call(
                lambda: retry_handler.execute(make_request)
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "headers": dict(response.headers)
            }
            
        except Exception as e:
            self.logger.error("HTTP request failed", error=str(e), endpoint=endpoint)
            return {
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session manager and circuit breaker statistics"""
        return {
            "session_manager": self._session_manager.get_stats(),
            "circuit_breaker": self._circuit_breaker.get_stats()
        }
    
    async def cleanup(self):
        """Clean up all sessions and resources"""
        await self._session_manager.cleanup_all()
        self._circuit_breaker.reset()