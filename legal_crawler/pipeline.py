"""Async pipeline orchestration (fetcher -> parser -> storage).

Coordinates the full crawl:
1. Paginate the search API to collect all judicial-interpretation rows.
2. Fetch detail for each document (including ``lsyg`` historical versions).
3. Download document files (docx) via the batch-download API.
4. Download related materials (修改决定, 公告, etc.).
5. Persist everything to disk.
"""

import asyncio

from loguru import logger

from legal_crawler.config import config
from legal_crawler.fetcher import Fetcher
from legal_crawler.models import (
    DocumentDetail,
    HistoricalVersion,
    MaterialDetail,
    SearchResultRow,
)
from legal_crawler.parser import (
    parse_batch_download,
    parse_detail,
    parse_material_detail,
    parse_search_response,
)
from legal_crawler.storage import (
    detail_json_exists,
    file_exists,
    save_detail_json,
    save_document_file,
    save_index,
    save_material_file,
)


async def collect_search_rows(fetcher: Fetcher) -> list[SearchResultRow]:
    """Paginate the search API and return all rows."""
    all_rows: list[SearchResultRow] = []

    # First page to learn total count
    page_num = 1
    raw = await fetcher.fetch_search_page(page_num)
    resp = parse_search_response(raw)
    total = resp.total
    all_rows.extend(resp.rows)
    logger.info("Search total: {} documents (page {}/{})", total, page_num, _total_pages(total))

    total_pages = _total_pages(total)
    for page_num in range(2, total_pages + 1):
        raw = await fetcher.fetch_search_page(page_num)
        resp = parse_search_response(raw)
        all_rows.extend(resp.rows)
        logger.info("Fetched page {}/{} ({} rows)", page_num, total_pages, len(resp.rows))

    logger.info("Collected {} rows across {} pages", len(all_rows), total_pages)
    return all_rows


def _total_pages(total: int) -> int:
    """Calculate total pages given the row count and page size."""
    return (total + config.page_size - 1) // config.page_size


async def process_document(fetcher: Fetcher, row: SearchResultRow) -> DocumentDetail | None:
    """Fetch and store detail + download file for a single document."""
    try:
        # Skip if detail JSON already exists
        if await detail_json_exists(row.title, row.gbrq):
            logger.debug("Skipping (already saved): {}", row.title)
            return None

        # Fetch detail
        raw = await fetcher.fetch_detail(row.bbbs)
        detail = parse_detail(raw)
        logger.info(
            "Detail: {} | sxx={} | lsyg={} | xgzl={}",
            detail.title,
            detail.sxx,
            len(detail.lsyg or []),
            len(detail.xgzl),
        )

        # Save detail JSON (includes lsyg, xgzl metadata)
        await save_detail_json(detail)

        # Download the main document file
        if config.download_documents and detail.oss_file:
            await _download_document_file(fetcher, detail)

        # Download related materials
        if config.download_materials and detail.xgzl:
            await _download_materials(fetcher, detail)

        return detail

    except Exception:
        logger.exception("Failed to process document: {}", row.title)
        return None


async def _download_document_file(fetcher: Fetcher, detail: DocumentDetail) -> None:
    """Download the main document file via batch-download API."""
    if await file_exists(detail.title, detail.gbrq, config.download_format):
        logger.debug("Document file already exists: {}", detail.title)
        return

    items = [{"bbbs": detail.bbbs, "format": config.download_format}]
    raw = await fetcher.fetch_batch_download_urls(items)
    dl_resp = parse_batch_download(raw)

    if not dl_resp.data:
        logger.warning("No download URL returned for: {}", detail.title)
        return

    url = dl_resp.data[0].url
    data = await fetcher.get_bytes(url)
    await save_document_file(detail.title, detail.gbrq, config.download_format, data)


async def _download_materials(fetcher: Fetcher, detail: DocumentDetail) -> None:
    """Download all related materials (xgzl) for a document."""
    for mat in detail.xgzl:
        try:
            raw = await fetcher.fetch_material_detail(mat.file_id, detail.bbbs)
            mat_detail: MaterialDetail = parse_material_detail(raw)

            if not mat_detail.oss_file_path:
                logger.warning("No file path for material: {}", mat.title)
                continue

            # Build download URL from OSS path
            # The batch-download API doesn't support materials, so we
            # construct the OSS URL directly from the path.
            # We use the download/pc endpoint instead.
            dl_url = _build_material_download_url(mat_detail)
            if dl_url is None:
                logger.warning("Cannot build download URL for material: {}", mat.title)
                continue

            data = await fetcher.get_bytes(dl_url)
            ext = mat.file_type or "docx"
            await save_material_file(mat.title, ext, data)

        except Exception:
            logger.exception("Failed to download material: {}", mat.title)


def _build_material_download_url(mat: MaterialDetail) -> str | None:
    """Build a download URL for a material from its OSS path.

    The material detail returns ``ossFilePath`` like
    ``prod/20201229/xxxx.docx``.  The OSS base URL is the same
    one used by the batch-download API.
    """
    if not mat.oss_file_path:
        return None

    # OSS bucket base — extracted from batch-download response URLs.
    oss_base = "https://flkoss.obs-bj2.cucloud.cn"
    return f"{oss_base}/{mat.oss_file_path}"


async def process_historical_versions(fetcher: Fetcher, detail: DocumentDetail) -> list[DocumentDetail | None]:
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

    logger.info(
        "Processing {} historical versions for: {}",
        len(historical),
        detail.title,
    )

    tasks = [_fetch_historical_detail(fetcher, v) for v in historical]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Filter out BaseException instances from return_exceptions=True
    return [r if isinstance(r, DocumentDetail) else None for r in results]


async def _fetch_historical_detail(fetcher: Fetcher, version: HistoricalVersion) -> DocumentDetail | None:
    """Fetch and store a single historical version."""
    try:
        if await detail_json_exists(version.title, version.gbrq):
            logger.debug("Historical detail already saved: {} {}", version.title, version.gbrq)
            return None

        raw = await fetcher.fetch_detail(version.bbbs)
        hist_detail = parse_detail(raw)
        await save_detail_json(hist_detail)

        if config.download_documents and hist_detail.oss_file:
            await _download_document_file(fetcher, hist_detail)

        logger.info("Historical version saved: {} ({})", version.title, version.gbrq)
        return hist_detail

    except Exception:
        logger.exception("Failed to fetch historical version: {} {}", version.title, version.gbrq)
        return None


async def run_pipeline() -> None:
    """Run the full crawl pipeline."""
    logger.info("Starting judicial-interpretation crawler")

    async with Fetcher() as fetcher:
        # 1. Collect all search rows
        rows = await collect_search_rows(fetcher)
        await save_index(rows)

        # 2. Process each document (detail + download + historical versions)
        sem = asyncio.Semaphore(config.max_concurrency)

        async def process_with_sem(row: SearchResultRow) -> None:
            async with sem:
                detail = await process_document(fetcher, row)
                if detail is not None:
                    await process_historical_versions(fetcher, detail)

        await asyncio.gather(*(process_with_sem(r) for r in rows))

    logger.info("Crawler finished — {} documents processed", len(rows))
