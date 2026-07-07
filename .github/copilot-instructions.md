# Legal Crawler — Project Guidelines

## Overview

Asynchronous crawler for Chinese legal documents (laws, judicial interpretations, criminal law, etc.). Output aligns with the existing `assets/datasets/` directory structure (TXT/JSON files named by law and date).

## Tech Stack

- **Language**: Python 3.13+
- **HTTP**: aiohttp (async) — not requests/httpx
- **Parsing**: BeautifulSoup4 + lxml
- **Models**: Pydantic v2
- **Retry**: tenacity (`AsyncRetrying`)
- **Logging**: loguru (`from loguru import logger`)
- **Type checking**: ty (strict mode, `all = "error"`)
- **Linting**: ruff (config in `ruff.toml`, user-managed)
- **Package manager**: uv

## Architecture

Mirrors the TS `src/api/` structure: a low-level HTTP client plus per-domain API modules that return typed Pydantic models.

```
api/client.py   (async HTTP transport: aiohttp + retry + semaphore)
        ↓
api/search.py   api/detail.py   api/download.py   api/material.py
  (typed business functions: call client → return Pydantic models)
        ↓                                                          ← parser.py (sync text helpers)
pipeline.py  (async orchestration)  →  storage.py  (async IO)      ← models.py  (pydantic schemas)
```

- **api/client**: Low-level async HTTP via `aiohttp.ClientSession`. Handles retries, rate limiting, headers. Returns `dict[str, Any]` / `bytes` — knows nothing about business endpoints.
- **api/{search,detail,download,material}**: Per-domain API functions. Each calls the client and returns a typed Pydantic model (e.g. `fetch_detail() -> DocumentDetail`). Fetch + parse are co-located here.
- **parser**: Synchronous text helpers only (`strip_highlight_tags`). No endpoint-specific JSON parsing — that lives in the `api/` modules.
- **models**: Pydantic models defining the schema for crawled items.
- **storage**: Async persistence (files, DB). All IO is `async def`.
- **pipeline**: Orchestrates api → storage with `asyncio.gather` for concurrency.
- **config**: Crawler settings (URLs, concurrency, rate limits, retry params).
- **utils**: Logging, path helpers. No business logic here.

## Build & Test Commands

```bash
uv sync                          # Install dependencies
uv run ruff check --fix .        # Auto-fix lint + format
uv run ruff check .              # Check lint + format (no changes)
uv run ty check .                # Type check with ty
uv run pytest -vv                # Run pytest
```

## Conventions

- **IO layers are async**: `api/client`, `storage`, `pipeline` use `async def`. Entry point uses `asyncio.run()`.
- **Pure compute is sync**: `parser` functions are synchronous — no network/file IO.
- **All data models are Pydantic**: Define schemas in `models.py`, not inline dicts.
- **API functions return Pydantic models**: `api/*.py` functions call the client and return typed models — callers never handle raw `dict` or `Any`.
- **No business logic in `utils.py`**: Only generic helpers (path normalization, filename building).
- **Absolute imports only**: `from legal_crawler.config import config` — never `from .config import config`.
- **No `from __future__ import annotations`**: Python 3.13 supports `X | Y` natively.
- **Logging via loguru**: `from legal_crawler.utils import logger` — never use stdlib `logging`, and never `from loguru import logger` in business modules (only `utils/logging.py` does that). Importing from `legal_crawler.utils` configures the sinks on first import — no `setup_logging()` call needed.
- **Use f-strings for log messages**: `logger.info(f"Saved {count} files")` — never use loguru's `{}` placeholder syntax with positional args, nor printf-style `%s`.
- **Output format**: Match existing `assets/datasets/` conventions (e.g., `中华人民共和国刑法_20201226.txt`).
- **Don't duplicate linter-enforced rules here**: ruff and ty configs handle formatting, import order, type annotations. These guidelines cover what linters can't enforce.
