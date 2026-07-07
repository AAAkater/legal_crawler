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
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from legal_crawler.config import config
from legal_crawler.utils import logger


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
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.timeout),
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json;charset=UTF-8",
                "Referer": "https://flk.npc.gov.cn/search",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
                ),
            },
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

    async def _sleep(self) -> None:
        """Rate-limit between requests."""
        if config.request_delay > 0:
            await asyncio.sleep(config.request_delay)

    def _retrying(self) -> AsyncRetrying:
        """Build a fresh ``AsyncRetrying`` instance for one call."""
        return AsyncRetrying(
            retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
            stop=stop_after_attempt(config.max_retries),
            wait=wait_exponential(multiplier=1, max=config.retry_max_wait),
            reraise=True,
        )

    # ── public API ─────────────────────────────────────────────────
    async def post(self, url: str, payload: Any) -> dict[str, Any]:
        """POST a JSON payload and return the parsed JSON response (dict)."""
        async with self._semaphore:
            async for attempt in self._retrying():
                with attempt:
                    await self._sleep()
                    logger.debug(f"POST {url}")
                    async with self.session.post(url, json=payload) as resp:
                        resp.raise_for_status()
                        return await resp.json()

            # Unreachable — reraise=True guarantees an exception escapes.
            raise RuntimeError("unreachable")

    async def get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        """GET with query params and return the parsed JSON response (dict)."""
        async with self._semaphore:
            async for attempt in self._retrying():
                with attempt:
                    await self._sleep()
                    logger.debug(f"GET {url} params={params}")
                    async with self.session.get(url, params=params) as resp:
                        resp.raise_for_status()
                        return await resp.json()

            raise RuntimeError("unreachable")

    async def get_bytes(self, url: str) -> bytes:
        """GET raw bytes (for file downloads)."""
        async with self._semaphore:
            async for attempt in self._retrying():
                with attempt:
                    await self._sleep()
                    logger.debug(f"GET (bytes) {url[:120]}")
                    async with self.session.get(url) as resp:
                        resp.raise_for_status()
                        return await resp.read()

            raise RuntimeError("unreachable")
