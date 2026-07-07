"""Async pipeline orchestration (api -> storage).

Coordinates the full crawl:
1. Paginate the search API to collect all judicial-interpretation rows.
2. Fetch detail for each document (including ``lsyg`` historical versions).
3. Download document files (docx) via the batch-download API.
4. Download related materials (修改决定, 公告, etc.).
5. Persist everything to disk.
"""

import asyncio

from loguru import logger

from legal_crawler.api import (
    HttpClient,
    build_material_download_url,
    download_document_bytes,
    fetch_detail,
    fetch_material_detail,
    fetch_search_page,
)
from legal_crawler.config import config
from legal_crawler.models import DocumentDetail, HistoricalVersion, SearchResultRow
from legal_crawler.storage import (
    detail_json_exists,
    file_exists,
    save_detail_json,
    save_document_file,
    save_index,
    save_material_file,
)


async def collect_search_rows(client: HttpClient) -> list[SearchResultRow]:
    """Paginate the search API and return all rows."""
    all_rows: list[SearchResultRow] = []

    # First page to learn total count
    page_num = 1
    resp = await fetch_search_page(client, page_num)
    total = resp.total
    all_rows.extend(resp.rows)
    logger.info(f"Search total: {total} documents (page {page_num}/{_total_pages(total)})")

    total_pages = _total_pages(total)
    for page_num in range(2, total_pages + 1):
        resp = await fetch_search_page(client, page_num)
        all_rows.extend(resp.rows)
        logger.info(f"Fetched page {page_num}/{total_pages} ({len(resp.rows)} rows)")

    logger.info(f"Collected {len(all_rows)} rows across {total_pages} pages")
    return all_rows


def _total_pages(total: int) -> int:
    """Calculate total pages given the row count and page size."""
    return (total + config.page_size - 1) // config.page_size


async def process_document(client: HttpClient, row: SearchResultRow) -> DocumentDetail | None:
    """Fetch and store detail + download file for a single document."""
    try:
        # Skip if detail JSON already exists
        if await detail_json_exists(row.title, row.gbrq):
            logger.debug(f"Skipping (already saved): {row.title}")
            return None

        # Fetch detail (typed)
        detail = await fetch_detail(client, row.bbbs)
        logger.info(
            f"Detail: {detail.title} | sxx={detail.sxx} | lsyg={len(detail.lsyg or [])} | xgzl={len(detail.xgzl)}"
        )

        # Save detail JSON (includes lsyg, xgzl metadata)
        await save_detail_json(detail)

        # Download the main document file
        if config.download_documents and detail.oss_file:
            await _download_document_file(client, detail)

        # Download related materials
        if config.download_materials and detail.xgzl:
            await _download_materials(client, detail)

        return detail

    except Exception:
        logger.exception(f"Failed to process document: {row.title}")
        return None


async def _download_document_file(client: HttpClient, detail: DocumentDetail) -> None:
    """Download the main document file via batch-download API."""
    if await file_exists(detail.title, detail.gbrq, config.download_format):
        logger.debug(f"Document file already exists: {detail.title}")
        return

    data = await download_document_bytes(client, detail.bbbs, config.download_format)
    if data is None:
        logger.warning(f"No download URL returned for: {detail.title}")
        return

    await save_document_file(detail.title, detail.gbrq, config.download_format, data)


async def _download_materials(client: HttpClient, detail: DocumentDetail) -> None:
    """Download all related materials (xgzl) for a document."""
    for mat in detail.xgzl:
        try:
            mat_detail = await fetch_material_detail(client, mat.file_id, detail.bbbs)

            dl_url = build_material_download_url(mat_detail)
            if dl_url is None:
                logger.warning(f"No file path for material: {mat.title}")
                continue

            data = await client.get_bytes(dl_url)
            ext = mat.file_type or "docx"
            await save_material_file(mat.title, ext, data)

        except Exception:
            logger.exception(f"Failed to download material: {mat.title}")


async def process_historical_versions(client: HttpClient, detail: DocumentDetail) -> list[DocumentDetail | None]:
    """Fetch and store details for all historical versions (lsyg).

    Each historical version has its own ``bbbs`` and can be fetched
    via the same detail API.  This preserves the full version history
    needed for DPO chosen/rejected pairs.
    """
    if not detail.lsyg or not config.download_historical:
        return []

    # Skip the current version (it's already in detail)
    historical = [v for v in detail.lsyg if v.bbbs != detail.bbbs]
    if not historical:
        return []

    logger.info(f"Processing {len(historical)} historical versions for: {detail.title}")

    tasks = [_fetch_historical_detail(client, v) for v in historical]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Filter out BaseException instances from return_exceptions=True
    return [r if isinstance(r, DocumentDetail) else None for r in results]


async def _fetch_historical_detail(client: HttpClient, version: HistoricalVersion) -> DocumentDetail | None:
    """Fetch and store a single historical version."""
    try:
        if await detail_json_exists(version.title, version.gbrq):
            logger.debug(f"Historical detail already saved: {version.title} {version.gbrq}")
            return None

        hist_detail = await fetch_detail(client, version.bbbs)
        await save_detail_json(hist_detail)

        if config.download_documents and hist_detail.oss_file:
            await _download_document_file(client, hist_detail)

        logger.info(f"Historical version saved: {version.title} ({version.gbrq})")
        return hist_detail

    except Exception:
        logger.exception(f"Failed to fetch historical version: {version.title} {version.gbrq}")
        return None


async def run_pipeline() -> None:
    """Run the full crawl pipeline."""
    logger.info("Starting judicial-interpretation crawler")

    async with HttpClient() as client:
        # 1. Collect all search rows
        rows = await collect_search_rows(client)
        await save_index(rows)

        # 2. Process each document (detail + download + historical versions)
        sem = asyncio.Semaphore(config.max_concurrency)

        async def process_with_sem(row: SearchResultRow) -> None:
            async with sem:
                detail = await process_document(client, row)
                if detail is not None:
                    await process_historical_versions(client, detail)

        await asyncio.gather(*(process_with_sem(r) for r in rows))

    logger.info(f"Crawler finished — {len(rows)} documents processed")
