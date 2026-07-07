"""Asynchronous storage layer.

All IO is ``async def``.  Files are written to the output directory
structure defined in ``config.py``.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger

from legal_crawler.config import config
from legal_crawler.models import DocumentDetail, SearchResultRow
from legal_crawler.utils import (
    build_document_filename,
    build_material_filename,
    ensure_dir,
)


async def save_document_file(title: str, gbrq: str, ext: str, data: bytes) -> Path:
    """Save a main document file (docx/pdf) to the documents directory."""
    filename = build_document_filename(title, gbrq, ext)
    path = ensure_dir(config.documents_dir) / filename
    path.write_bytes(data)
    logger.info("Saved document: %s (%d bytes)", path.name, len(data))
    return path


async def save_material_file(title: str, ext: str, data: bytes) -> Path:
    """Save a related-material file to the materials directory."""
    filename = build_material_filename(title, ext)
    path = ensure_dir(config.materials_dir) / filename
    path.write_bytes(data)
    logger.info("Saved material: %s (%d bytes)", path.name, len(data))
    return path


async def save_detail_json(detail: DocumentDetail) -> Path:
    """Save a document's full detail (including lsyg) as JSON."""
    filename = build_document_filename(detail.title, detail.gbrq, "json")
    path = ensure_dir(config.documents_dir) / filename
    path.write_text(
        detail.model_dump_json(by_alias=True, indent=2),
        encoding="utf-8",
    )
    logger.debug("Saved detail JSON: %s", path.name)
    return path


async def save_index(rows: list[SearchResultRow]) -> Path:
    """Save the full search index (all rows from all pages) as JSON."""
    path = config.output_dir / config.metadata_filename
    ensure_dir(config.output_dir)
    payload: dict[str, Any] = {
        "total": len(rows),
        "rows": [r.model_dump(by_alias=True) for r in rows],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved index: %s (%d rows)", path.name, len(rows))
    return path


async def file_exists(title: str, gbrq: str, ext: str) -> bool:
    """Check whether a document file has already been downloaded."""
    filename = build_document_filename(title, gbrq, ext)
    return (config.documents_dir / filename).exists()


async def detail_json_exists(title: str, gbrq: str) -> bool:
    """Check whether a detail JSON has already been saved."""
    filename = build_document_filename(title, gbrq, "json")
    return (config.documents_dir / filename).exists()
