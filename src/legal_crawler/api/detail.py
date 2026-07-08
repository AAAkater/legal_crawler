"""Document detail API (``/law-search/search/flfgDetails``).

Fetches the full detail for a single document (by ``bbbs``) and
returns a typed ``DocumentDetail`` model.
"""

from legal_crawler.api.client import HttpClient
from legal_crawler.config import config
from legal_crawler.models import DocumentDetail
from legal_crawler.parser import strip_highlight_tags


async def fetch_detail(client: HttpClient, bbbs: str) -> DocumentDetail:
    """Fetch document detail for *bbbs* and return a typed model.

    The API wraps the actual data in ``{"data": {...}}``.  Highlight
    tags are stripped from the title and from any historical-version
    (``lsyg``) titles.
    """
    raw = await client.get(config.detail_url, {"bbbs": bbbs})

    data = raw["data"]
    if "title" in data:
        data["title"] = strip_highlight_tags(data["title"])

    # Clean lsyg titles too
    for item in data.get("lsyg", []):
        if "title" in item:
            item["title"] = strip_highlight_tags(item["title"])

    return DocumentDetail.model_validate(data)
