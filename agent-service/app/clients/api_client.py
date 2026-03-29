"""
Internal API Client
HTTP client for communicating with api-service via Docker internal network.
"""

import httpx
import structlog
from typing import Any, Dict, Optional

from app.core.config import settings

logger = structlog.get_logger()

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5  # seconds: 0.5, 1.0, 2.0


class InternalApiClient:
    """
    HTTP client for internal communication with api-service.

    Propagates the user's auth token on every request to ensure
    api-service enforces authorization (user only sees own resources).
    """

    def __init__(self):
        self._base_url = settings.API_SERVICE_URL.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=30.0,
                    write=10.0,
                    pool=5.0,
                ),
            )
        return self._client

    def _auth_headers(self, token: str) -> Dict[str, str]:
        """Build authorization headers from user token."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get(
        self,
        path: str,
        token: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """GET request to api-service with auth token propagation."""
        return await self._request("GET", path, token, params=params)

    async def post(
        self,
        path: str,
        token: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """POST request to api-service with auth token propagation."""
        return await self._request("POST", path, token, json_data=data)

    async def put(
        self,
        path: str,
        token: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """PUT request to api-service with auth token propagation."""
        return await self._request("PUT", path, token, json_data=data)

    async def delete(
        self,
        path: str,
        token: str,
    ) -> Any:
        """DELETE request to api-service with auth token propagation."""
        return await self._request("DELETE", path, token)

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute an HTTP request with retry logic and structured logging.
        Retries on 5xx errors and timeouts with exponential backoff.
        """
        client = await self._get_client()
        headers = self._auth_headers(token)
        last_exception: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    headers=headers,
                    params=params,
                    json=json_data,
                )

                logger.debug(
                    "API request completed",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    attempt=attempt + 1,
                )

                if response.status_code >= 500:
                    last_exception = httpx.HTTPStatusError(
                        f"Server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    if attempt < MAX_RETRIES - 1:
                        import asyncio

                        wait = RETRY_BACKOFF_FACTOR * (2**attempt)
                        logger.warning(
                            "Retrying after server error",
                            method=method,
                            path=path,
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            wait_seconds=wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise last_exception

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    wait = RETRY_BACKOFF_FACTOR * (2**attempt)
                    logger.warning(
                        "Retrying after timeout",
                        method=method,
                        path=path,
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                logger.error(
                    "API request failed after retries",
                    method=method,
                    path=path,
                    error=str(e),
                    attempts=MAX_RETRIES,
                )
                raise

            except httpx.HTTPStatusError:
                # Non-5xx errors: don't retry (4xx are client errors)
                raise

            except Exception as e:
                logger.error(
                    "Unexpected API client error",
                    method=method,
                    path=path,
                    error=str(e),
                )
                raise

        raise last_exception  # Should not reach here

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Singleton instance
internal_api_client = InternalApiClient()
