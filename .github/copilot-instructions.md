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

```
fetcher.py  (async IO)  →  parser.py  (sync compute)  →  models.py  (pydantic)
                                                          ↓
pipeline.py  (async orchestration)  →  storage.py  (async IO)
```

- **fetcher**: Async HTTP via `aiohttp.ClientSession`. Handles retries, rate limiting, headers.
- **parser**: Synchronous HTML/JSON → structured data. Pure functions, no IO.
- **models**: Pydantic models defining the schema for crawled items.
- **storage**: Async persistence (files, DB). All IO is `async def`.
- **pipeline**: Orchestrates fetcher → parser → storage with `asyncio.gather` for concurrency.
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

- **IO layers are async**: `fetcher`, `storage`, `pipeline` use `async def`. Entry point uses `asyncio.run()`.
- **Pure compute is sync**: `parser` functions are synchronous — no network/file IO.
- **All data models are Pydantic**: Define schemas in `models.py`, not inline dicts.
- **No business logic in `utils.py`**: Only generic helpers (path normalization, filename building).
- **Absolute imports only**: `from legal_crawler.config import config` — never `from .config import config`.
- **No `from __future__ import annotations`**: Python 3.13 supports `X | Y` natively.
- **Logging via loguru**: `from loguru import logger` — never use stdlib `logging`.
- **Output format**: Match existing `assets/datasets/` conventions (e.g., `中华人民共和国刑法_20201226.txt`).
- **Don't duplicate linter-enforced rules here**: ruff and ty configs handle formatting, import order, type annotations. These guidelines cover what linters can't enforce.
