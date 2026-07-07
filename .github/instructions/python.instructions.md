---
description: "Use when writing Python code, async crawlers, aiohttp HTTP clients, BeautifulSoup parsers, or Pydantic models. Covers async patterns, type annotations, retry strategy, and error handling."
applyTo: "**/*.py"
---

# Python Coding Guidelines

## Async Patterns

- **IO layers use `async def`**: `fetcher.py`, `storage.py`, `pipeline.py` — all network and file operations are async.
- **Pure compute is sync**: `parser.py` functions are synchronous. Don't make CPU-bound functions async.
- **Entry point**: Use `asyncio.run(main())` in `__main__.py`. The `main()` function is `async def`.
- **Concurrency**: Use `asyncio.gather()` for batch operations. Always pair with `asyncio.Semaphore` to limit concurrency and avoid getting blocked.

## aiohttp Usage

- **Always use context managers**: `async with aiohttp.ClientSession() as session:` — never create a session without `async with`.
- **Set explicit timeout**: `aiohttp.ClientTimeout(total=30)` — never rely on defaults.
- **Check response status**: Call `response.raise_for_status()` after every request. Never ignore non-2xx responses.
- **Read body inside the context**: `await response.text()` or `await response.read()` must be called before exiting the `async with` block.

```python
# Correct
async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
    async with session.get(url) as resp:
        resp.raise_for_status()
        html = await resp.text()

# Wrong — don't do this
session = aiohttp.ClientSession()
resp = await session.get(url)
html = resp.text  # missing await, missing context manager
```

## Type Annotations

- **All functions need complete annotations**: parameters and return types. ty runs in strict mode (`all = "error"`).
- **No bare generics**: Use `list[str]` not `list`, `dict[str, int]` not `dict`, `tuple[int, ...]` not `tuple`.
- **Use `from __future__ import annotations`** if needed for forward references, but prefer modern syntax (Python 3.13 supports `X | Y` natively).

## Retry Strategy

- **Use `tenacity.AsyncRetrying`** for async retry logic. Don't hand-write retry loops.
- **Distinguish retryable vs fatal errors**:
  - Retryable: `aiohttp.ClientError`, `asyncio.TimeoutError`, HTTP 5xx
  - Fatal: HTTP 4xx (except 429), parsing errors, validation errors
- **Use exponential backoff**: `tenacity.wait_exponential(multiplier=1, max=60)` with a max retry count.

```python
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

async for attempt in AsyncRetrying(
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=60),
):
    with attempt:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()
```

## Error Handling

- **Network errors**: Catch `aiohttp.ClientError` and `asyncio.TimeoutError` at the fetcher layer. Log and re-raise for retry, or wrap in a custom exception.
- **HTTP status errors**: `raise_for_status()` raises `aiohttp.ClientResponseError` — catch at fetcher layer to decide retry vs skip.
- **Parsing errors**: Catch `BeautifulSoup` / `lxml` exceptions at the parser layer. Log the URL and skip the item — don't crash the pipeline.
- **Don't swallow exceptions silently**: Always log before catching and continuing.

## Concurrency Control

- **Limit concurrent requests**: `asyncio.Semaphore(n)` where `n` is configured in `config.py`. Default to 5-10 for legal document sites.
- **Rate limit between requests**: `await asyncio.sleep(delay)` after each request if needed.
- **Batch with gather**: `await asyncio.gather(*tasks)` but wrap each task with the semaphore.

```python
sem = asyncio.Semaphore(5)

async def fetch_one(url: str) -> str:
    async with sem:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

results = await asyncio.gather(*(fetch_one(u) for u in urls))
```
