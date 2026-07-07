"""Batch-download API (``/law-search/download/batch``).

Fetches download URLs for documents, then downloads the raw bytes.
"""

import json

from legal_crawler.api.client import HttpClient
from legal_crawler.config import config
from legal_crawler.models import BatchDownloadResponse


async def fetch_batch_download_urls(
    client: HttpClient,
    items: list[dict[str, str]],
) -> BatchDownloadResponse:
    """Fetch download URLs for a batch of ``[{"bbbs": ..., "format": ...}]``.

    Returns a typed ``BatchDownloadResponse`` model.
    """
    raw = await client.post_json(
        config.batch_download_url,
        json.loads(json.dumps(items)),  # ensure plain JSON
    )

    if not isinstance(raw, dict):
        raise ValueError(f"Expected dict for download response, got {type(raw)}")

    return BatchDownloadResponse.model_validate(raw)


async def download_document_bytes(
    client: HttpClient,
    bbbs: str,
    fmt: str | None = None,
) -> bytes | None:
    """Download a single document's file bytes via the batch-download API.

    Returns ``None`` if no download URL was returned for the document.
    """
    fmt = fmt or config.download_format
    resp = await fetch_batch_download_urls(client, [{"bbbs": bbbs, "format": fmt}])

    if not resp.data:
        return None

    return await client.get_bytes(resp.data[0].url)
