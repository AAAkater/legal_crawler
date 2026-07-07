"""Typed API layer for the legal-document crawler.

Mirrors the TS ``src/api/`` structure:

- ``client``    — low-level HTTP transport (aiohttp + retry + semaphore)
- ``search``    — search-list pagination API
- ``detail``    — document detail API
- ``download``  — batch-download API
- ``material``  — related-material API

Each business module exposes async functions that call the client and
return Pydantic models, so callers never deal with raw ``dict`` or
``Any``.
"""

from legal_crawler.api.client import HttpClient
from legal_crawler.api.detail import fetch_detail
from legal_crawler.api.download import download_document_bytes, fetch_batch_download_urls
from legal_crawler.api.material import (
    build_material_download_url,
    download_material_bytes,
    fetch_material_detail,
)
from legal_crawler.api.search import fetch_all_search_rows, fetch_search_page

__all__ = [
    "HttpClient",
    "build_material_download_url",
    "download_document_bytes",
    "download_material_bytes",
    "fetch_all_search_rows",
    "fetch_batch_download_urls",
    "fetch_detail",
    "fetch_material_detail",
    "fetch_search_page",
]
