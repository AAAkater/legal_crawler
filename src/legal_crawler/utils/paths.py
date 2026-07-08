"""Path and filename helpers."""

from pathlib import Path

from legal_crawler.config import config


def ensure_dir(path: Path) -> Path:
    """Create *path* (recursively) if it does not exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    """Replace characters that are illegal in filenames with underscores."""
    illegal = set('<>:"/\\|?*')
    return "".join("_" if ch in illegal else ch for ch in name).strip()


def build_document_filename(title: str, gbrq: str, ext: str) -> str:
    """Build a filename following the project convention.

    Example: ``最高人民法院关于…的解释_20201229.docx``
    """
    date_compact = gbrq.replace("-", "")
    return f"{sanitize_filename(title)}_{date_compact}.{ext}"


def build_material_filename(title: str, ext: str) -> str:
    """Build a filename for a related-material file."""
    return f"{sanitize_filename(title)}.{ext}"


def output_documents_dir() -> Path:
    """Return the documents output directory, creating it if needed."""
    return ensure_dir(config.documents_dir)


def output_materials_dir() -> Path:
    """Return the materials output directory, creating it if needed."""
    return ensure_dir(config.materials_dir)
