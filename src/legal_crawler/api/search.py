"""Search-list API (``/law-search/search/list``)."""

from legal_crawler.api.client import HttpClient
from legal_crawler.config import config
from legal_crawler.models import SearchListRequest, SearchResponse, SearchResultRow


async def fetch_search_page(
    client: HttpClient,
    page_num: int = 1,
    page_size: int = 20,
    effectiveness_filter: list[int] = config.effectiveness_filter,
) -> SearchResponse:
    """Fetch one page of the search-list API and return a typed model."""
    payload = SearchListRequest.model_validate(
        {
            "effectiveness_filter": effectiveness_filter,
            "law_category_ids": config.law_category_ids,
            "page_num": page_num,
            "page_size": page_size,
        }
    ).model_dump(by_alias=True)

    raw = await client.post(config.search_list_url, payload)
    return SearchResponse.model_validate(raw)


async def fetch_all_search_rows(
    client: HttpClient,
    effectiveness_filter: list[int] = config.effectiveness_filter,
) -> list[SearchResultRow]:
    """Paginate the search API and return all rows across every page.

    First requests page 1 with ``pageSize=20`` solely to obtain the
    ``total`` count.  Then re-fetches every page with ``pageSize=100``
    starting from page 1 so that the row set is always consistent.
    """
    initial_resp = await fetch_search_page(
        client,
        page_num=1,
        page_size=20,
        effectiveness_filter=effectiveness_filter,
    )
    total = initial_resp.total
    total_pages = (total + 99) // 100

    all_rows: list[SearchResultRow] = []
    for page_num in range(1, total_pages + 1):
        resp = await fetch_search_page(
            client, page_num=page_num, page_size=100, effectiveness_filter=effectiveness_filter
        )
        all_rows.extend(resp.rows)

    return all_rows
