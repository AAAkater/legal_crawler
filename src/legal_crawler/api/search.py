"""Search-list API (``/law-search/search/list``).

Business-domain functions that call the HTTP client and return
Pydantic models.  Equivalent of a TS ``api/search.ts`` module.
"""

from typing import Any

from legal_crawler.api.client import HttpClient
from legal_crawler.config import config
from legal_crawler.models import SearchResponse, SearchResultRow
from legal_crawler.parser import strip_highlight_tags


def _build_search_payload(
    page_num: int,
    flfg_code_ids: list[int] | None = None,
    sxx_filter: list[int] | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for one search-list page request."""
    return {
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


async def fetch_search_page(
    client: HttpClient,
    page_num: int,
    flfg_code_ids: list[int] | None = None,
    sxx_filter: list[int] | None = None,
) -> SearchResponse:
    """Fetch one page of the search-list API and return a typed model.

    Strips ``<em>`` highlight tags from titles so stored data is clean.
    """
    payload = _build_search_payload(page_num, flfg_code_ids, sxx_filter)
    raw = await client.post(config.search_list_url, payload)

    rows = raw.get("rows", [])
    for row in rows:
        if isinstance(row, dict) and "title" in row:
            row["title"] = strip_highlight_tags(row["title"])

    return SearchResponse.model_validate(raw)


async def fetch_all_search_rows(
    client: HttpClient,
    flfg_code_ids: list[int] | None = None,
    sxx_filter: list[int] | None = None,
) -> list[SearchResultRow]:
    """Paginate the search API and return all rows across every page."""
    all_rows: list[SearchResultRow] = []

    page_num = 1
    resp = await fetch_search_page(client, page_num, flfg_code_ids, sxx_filter)
    total = resp.total
    all_rows.extend(resp.rows)

    total_pages = (total + config.page_size - 1) // config.page_size
    for page_num in range(2, total_pages + 1):
        resp = await fetch_search_page(client, page_num, flfg_code_ids, sxx_filter)
        all_rows.extend(resp.rows)

    return all_rows
