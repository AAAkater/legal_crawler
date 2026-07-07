"""Asynchronous HTTP fetcher layer.

All network IO lives here.  Uses ``aiohttp.ClientSession`` with
context managers, explicit timeouts, and ``tenacity.AsyncRetrying``
for retry logic.
"""

import asyncio
import json
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

# Errors that are worth retrying.
_RETRYABLE = (aiohttp.ClientError, asyncio.TimeoutError)

# Default JSON headers for POST/GET API calls.
_JSON_HEADERS: dict[str, str] = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": "https://flk.npc.gov.cn/search",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    ),
}


class Fetcher:
    """Async HTTP client wrapping ``aiohttp.ClientSession``.

    Use as an async context manager::

        async with Fetcher() as fetcher:
            data = await fetcher.post_json(url, payload)
    """

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(config.max_concurrency)

    # ── context-manager protocol ───────────────────────────────────
    async def __aenter__(self) -> "Fetcher":
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
            raise RuntimeError("Fetcher used outside of 'async with'")
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
    async def post_json(self, url: str, payload: Any) -> Any:
        """POST a JSON payload and return the parsed JSON response."""
        async with self._semaphore:
            return await self._post_json_with_retry(url, payload)

    async def get_json(self, url: str, params: dict[str, str]) -> Any:
        """GET with query params and return the parsed JSON response."""
        async with self._semaphore:
            return await self._get_json_with_retry(url, params)

    async def get_bytes(self, url: str) -> bytes:
        """GET raw bytes (for file downloads)."""
        async with self._semaphore:
            return await self._get_bytes_with_retry(url)

    # ── retry-wrapped internals ────────────────────────────────────
    async def _post_json_with_retry(self, url: str, payload: Any) -> Any:
        async for attempt in self._retrying():
            with attempt:
                await self._sleep()
                logger.debug(f"POST {url}")
                async with self.session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()

        # Unreachable — reraise=True guarantees an exception escapes.
        raise RuntimeError("unreachable")

    async def _get_json_with_retry(self, url: str, params: dict[str, str]) -> Any:
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

    # ── high-level convenience methods ─────────────────────────────
    async def fetch_search_page(
        self,
        page_num: int,
        flfg_code_ids: list[int] | None = None,
        sxx_filter: list[int] | None = None,
    ) -> Any:
        """Fetch one page of the search-list API."""
        payload: dict[str, Any] = {
            "searchRange": 1,
            "sxrq": [],
            "gbrq": [],
            "searchType": 2,
            "sxx": sxx_filter if sxx_filter is not None else config.sxx_filter,
            "gbrqYear": [],
            "flfgCodeId": flfg_code_ids if flfg_code_ids is not None else config.flfg_code_ids,
            "zdjgCodeId": [],
            "searchContent": "",
            "xgzlSearch": False,
            "orderByParam": {"order": "-1", "sort": ""},
            "pageNum": page_num,
            "pageSize": config.page_size,
        }
        return await self.post_json(config.search_list_url, payload)

    async def fetch_detail(self, bbbs: str) -> Any:
        """Fetch document detail for *bbbs*."""
        return await self.get_json(config.detail_url, {"bbbs": bbbs})

    async def fetch_batch_download_urls(self, items: list[dict[str, str]]) -> Any:
        """Fetch download URLs for a batch of ``[{"bbbs": ..., "format": ...}]``."""
        return await self.post_json(
            config.batch_download_url,
            json.loads(json.dumps(items)),  # ensure plain JSON
        )

    async def fetch_material_detail(self, file_id: str, bbbs: str) -> Any:
        """Fetch detail for a related material."""
        return await self.get_json(
            config.material_detail_url,
            {"fileId": file_id, "bbbs": bbbs},
        )
