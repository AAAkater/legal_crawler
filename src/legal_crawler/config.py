"""Crawler configuration.

All tunable settings live here.  Import the ``config`` singleton
rather than constructing ``CrawlerConfig`` directly.

Uses ``pydantic-settings`` so values can be overridden via environment
variables, e.g. ``LEGAL_CRAWLER_MAX_CONCURRENCY=10``.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CrawlerConfig(BaseSettings):
    """Configuration for the judicial-interpretation crawler."""

    model_config = SettingsConfigDict(
        env_prefix="legal_crawler_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── API endpoints ──────────────────────────────────────────────
    base_url: str = "https://flk.npc.gov.cn"
    search_list_path: str = "/law-search/search/list"
    detail_path: str = "/law-search/search/flfgDetails"
    batch_download_path: str = "/law-search/download/batch"
    material_detail_path: str = "/law-search/search/xgzlDetails"

    # ── Search parameters ──────────────────────────────────────────
    # flfgCodeId=311 → 司法解释 (parent); 320/330/340/350 are child categories.
    law_category_ids: list[int] = Field(
        default_factory=lambda: [311, 320, 330, 340, 350],
        description="法律法规分类 code IDs. 311 = 司法解释; 320/330/340/350 = child categories.",
    )
    page_size: int = 20
    # Empty list matches the site search request and fetches all statuses.
    effectiveness_filter: list[int] = Field(
        default_factory=list,
        description="时效性 filter: []=全部, 1=已废止, 2=已修改, 3=有效.",
    )

    # ── Concurrency & rate limiting ────────────────────────────────
    max_concurrency: int = 5
    request_delay: float = 0.5  # seconds between requests per worker
    timeout: int = 30  # seconds

    # ── Retry ──────────────────────────────────────────────────────
    max_retries: int = 3
    retry_max_wait: int = 60  # seconds

    # ── Output ─────────────────────────────────────────────────────
    output_dir: Path = Field(
        default=Path("output"),
        description="Root output directory for crawled data.",
    )
    documents_subdir: str = "documents"
    materials_subdir: str = "materials"
    metadata_filename: str = "index.json"

    # ── Download ───────────────────────────────────────────────────
    download_format: str = "docx"  # "docx" or "pdf"
    download_documents: bool = True
    download_materials: bool = True
    download_historical: bool = True

    @property
    def search_list_url(self) -> str:
        """Full URL for the search-list endpoint."""
        return f"{self.base_url}{self.search_list_path}"

    @property
    def detail_url(self) -> str:
        """Full URL for the detail endpoint."""
        return f"{self.base_url}{self.detail_path}"

    @property
    def batch_download_url(self) -> str:
        """Full URL for the batch-download endpoint."""
        return f"{self.base_url}{self.batch_download_path}"

    @property
    def material_detail_url(self) -> str:
        """Full URL for the material-detail endpoint."""
        return f"{self.base_url}{self.material_detail_path}"

    @property
    def documents_dir(self) -> Path:
        """Directory for main document files."""
        return self.output_dir / self.documents_subdir

    @property
    def materials_dir(self) -> Path:
        """Directory for related-material files."""
        return self.output_dir / self.materials_subdir


config = CrawlerConfig()
