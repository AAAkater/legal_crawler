"""Utility helpers (logging, path handling, etc.).

No business logic here — only generic helpers.

Importing this package configures loguru sinks globally (via
``legal_crawler.utils.logging``), so logging is ready on first import.
"""

from legal_crawler.utils.logging import logger
from legal_crawler.utils.paths import (
    build_document_filename,
    build_material_filename,
    ensure_dir,
    output_documents_dir,
    output_materials_dir,
    sanitize_filename,
)

__all__ = [
    "build_document_filename",
    "build_material_filename",
    "ensure_dir",
    "logger",
    "output_documents_dir",
    "output_materials_dir",
    "sanitize_filename",
]
