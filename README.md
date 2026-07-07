# legal_crawler

Asynchronous legal document crawler.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run main.py
```

## Project Structure

```txt
legal_crawler/
├── __init__.py      # Package init
├── config.py        # Crawler configuration
├── fetcher.py       # Async HTTP fetcher (aiohttp)
├── parser.py        # Content parser (BeautifulSoup)
├── models.py        # Pydantic data models
├── storage.py       # Async storage layer
├── pipeline.py      # Async orchestration
└── utils.py         # Utilities
```

## Development

```bash
uv run ruff check --fix .   # Auto-fix style
uv run ruff check .         # Check style
uv run ty check .           # Type check
uv run pytest -vv           # Run tests
```
