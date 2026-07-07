"""Asynchronous HTTP client (low-level transport).

Wraps ``aiohttp.ClientSession`` with retry logic (tenacity),
concurrency limiting (semaphore), and rate limiting.  This is the
Python equivalent of the TS ``api/client.ts`` — it knows nothing
about business endpoints, only how to perform typed GET/POST/bytes
requests reliably.

Use as an async context manager::

    async with HttpClient() as client:
        data = await client.post_json(url, payload)
"""

import asyncio
from typing import Any

import aiohttp
from loguru import logger
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from legal_crawler.config import config

# Errors worth retrying: transient network/timeout failures.
_RETRYABLE: tuple[type[BaseException], ...] = (aiohttp.ClientError, asyncio.TimeoutError)

# Default JSON headers for POST/GET API calls.
_JSON_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://flk.npc.gov.cn/search",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}


class HttpClient:
    """Async HTTP client wrapping ``aiohttp.ClientSession``.

    Provides retry-wrapped ``post_json`` / ``get_json`` / ``get_bytes``
    primitives.  All requests pass through a semaphore (concurrency
    limit) and an optional rate-limit sleep.
    """

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(config.max_concurrency)

    # ── context-manager protocol ───────────────────────────────────
    async def __aenter__(self) -> "HttpClient":
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.timeout),
            headers=_JSON_HEADERS,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    # ── internal helpers ───────────────────────────────────────────
    @property
    def session(self) -> aiohttp.ClientSession:
        """Return the active session or raise if used outside ``async with``."""
        if self._session is None:
            raise RuntimeError("HttpClient used outside of 'async with'")
        return self._session

    def _retrying(self) -> AsyncRetrying:
        """Build a fresh ``AsyncRetrying`` instance for one call."""
        return AsyncRetrying(
            retry=retry_if_exception_type(_RETRYABLE),
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(multiplier=1, max=config.retry_max_wait),
            reraise=True,
        )

    async def _sleep(self) -> None:
        """Rate-limit between requests."""
        if config.request_delay > 0:
            await asyncio.sleep(config.request_delay)

    # ── public API ─────────────────────────────────────────────────
    async def post_json(self, url: str, payload: Any) -> dict[str, Any]:
        """POST a JSON payload and return the parsed JSON response (dict)."""
        async with self._semaphore:
            return await self._post_json_with_retry(url, payload)

    async def get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        """GET with query params and return the parsed JSON response (dict)."""
        async with self._semaphore:
            return await self._get_json_with_retry(url, params)

    async def get_bytes(self, url: str) -> bytes:
        """GET raw bytes (for file downloads)."""
        async with self._semaphore:
            return await self._get_bytes_with_retry(url)

    # ── retry-wrapped internals ────────────────────────────────────
    async def _post_json_with_retry(self, url: str, payload: Any) -> dict[str, Any]:
        async for attempt in self._retrying():
            with attempt:
                await self._sleep()
                logger.debug(f"POST {url}")
                async with self.session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()

        # Unreachable — reraise=True guarantees an exception escapes.
        raise RuntimeError("unreachable")

    async def _get_json_with_retry(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        async for attempt in self._retrying():
            with attempt:
                await self._sleep()
                logger.debug(f"GET {url} params={params}")
                async with self.session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()

        raise RuntimeError("unreachable")

    async def _get_bytes_with_retry(self, url: str) -> bytes:
        async for attempt in self._retrying():
            with attempt:
                await self._sleep()
                logger.debug(f"GET (bytes) {url[:120]}")
                async with self.session.get(url) as resp:
                    resp.raise_for_status()
                    return await resp.read()

        raise RuntimeError("unreachable")
