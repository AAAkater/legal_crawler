"""Content parser layer (JSON to structured data).

All functions here are **synchronous** — no network or file IO.
They accept raw JSON dicts (from the fetcher) and return Pydantic
models defined in ``models.py``.
"""

import re
from typing import Any
from urllib.parse import unquote

from legal_crawler.models import (
    BatchDownloadResponse,
    DocumentDetail,
    MaterialDetail,
    SearchResponse,
)

# Regex to strip ``<em class='highlight'>…</em>`` wrappers from titles.
_HIGHLIGHT_RE = re.compile(r"<em[^>]*>(.*?)</em>", re.DOTALL)


def strip_highlight_tags(text: str) -> str:
    """Remove ``<em class='highlight'>`` wrappers from *text*."""
    return _HIGHLIGHT_RE.sub(r"\1", text)


def parse_search_response(raw: Any) -> SearchResponse:
    """Parse the ``/law-search/search/list`` response.

    Strips ``<em>`` highlight tags from titles so stored data is clean.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict for search response, got {type(raw)}")

    rows = raw.get("rows", [])
    for row in rows:
        if isinstance(row, dict) and "title" in row:
            row["title"] = strip_highlight_tags(row["title"])

    return SearchResponse.model_validate(raw)


def parse_detail(raw: Any) -> DocumentDetail:
    """Parse the ``/law-search/search/flfgDetails`` response.

    The API wraps the actual data in ``{"data": {...}}``.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict for detail response, got {type(raw)}")

    data = raw.get("data")
    if data is None:
        raise ValueError("Detail response missing 'data' field")

    if isinstance(data, dict) and "title" in data:
        data["title"] = strip_highlight_tags(data["title"])

    # Clean lsyg titles too
    lsyg = data.get("lsyg")
    if isinstance(lsyg, list):
        for item in lsyg:
            if isinstance(item, dict) and "title" in item:
                item["title"] = strip_highlight_tags(item["title"])

    return DocumentDetail.model_validate(data)


def parse_batch_download(raw: Any) -> BatchDownloadResponse:
    """Parse the ``/law-search/download/batch`` response."""
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict for download response, got {type(raw)}")
    return BatchDownloadResponse.model_validate(raw)


def parse_material_detail(raw: Any) -> MaterialDetail:
    """Parse the ``/law-search/search/xgzlDetails`` response."""
    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict for material response, got {type(raw)}")

    data = raw.get("data")
    if data is None:
        raise ValueError("Material response missing 'data' field")

    return MaterialDetail.model_validate(data)


def extract_download_filename(url: str) -> str | None:
    """Extract the original filename from a download URL's query params.

    OSS URLs contain ``response-content-disposition=attachment; filename="…"``.
    """
    # Look for filename="..." in the URL
    match = re.search(r'filename%3D%22([^%"]+(?:%[0-9A-Fa-f]{2})*[^%"]*)', url)
    if not match:
        match = re.search(r'filename="([^"]+)"', url)
    if not match:
        return None

    return unquote(match.group(1))
