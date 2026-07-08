"""Pydantic data models for crawled judicial interpretations.

The national legal database (flk.npc.gov.cn) exposes a ``sxx`` field
that encodes the time-effectiveness status of a document:

    1 → 已废止 (repealed)
    2 → 已修改 (modified — has historical versions)
    3 → 有效 (effective)
    ``None`` → 修改、废止的决定 (modification/repeal decisions, no status code)

For DPO dataset construction:
    - chosen  = 有效(3) / 尚未生效 versions
    - rejected = 已修改(2) / 已废止(1) versions
"""

from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field


class Effectiveness(IntEnum):
    """Time-effectiveness status codes from the API ``sxx`` field."""

    REPEALED = 1  # 已废止
    MODIFIED = 2  # 已修改
    EFFECTIVE = 3  # 有效
    # NOTE: ``None`` means the item is a 修改、废止的决定 (no status code).


class OrderByParam(BaseModel):
    """Order-by parameter for the ``/law-search/search/list`` request."""

    order: str = Field(default="-1")
    sort: str = Field(default="")


class SearchListRequest(BaseModel):
    """Request payload for ``/law-search/search/list``."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    search_range: int = Field(default=1, alias="searchRange")
    effective_dates: list[str] = Field(default_factory=list, alias="sxrq")
    publish_dates: list[str] = Field(default_factory=list, alias="gbrq")
    search_type: int = Field(default=2, alias="searchType")
    effectiveness_filter: list[int] = Field(default_factory=list, alias="sxx")
    publish_years: list[str] = Field(default_factory=list, alias="gbrqYear")
    law_category_ids: list[int] = Field(alias="flfgCodeId")
    authority_ids: list[int] = Field(default_factory=list, alias="zdjgCodeId")
    search_content: str = Field(default="", alias="searchContent")
    order_by: OrderByParam = Field(default_factory=OrderByParam, alias="orderByParam")
    page_num: int = Field(alias="pageNum")
    page_size: int = Field(alias="pageSize")


class OssFile(BaseModel):
    """OSS file paths for downloadable document attachments."""

    model_config = ConfigDict(extra="ignore")

    oss_word_path: str | None = Field(default=None, alias="ossWordPath")
    oss_word_ofd_path: str | None = Field(default=None, alias="ossWordOfdPath")
    oss_word_ofd_size: int | None = Field(default=None, alias="ossWordOfdSize")
    oss_pdf_path: str | None = Field(default=None, alias="ossPdfPath")
    oss_pdf_ofd_path: str | None = Field(default=None, alias="ossPdfOfdPath")
    oss_pdf_ofd_size: int | None = Field(default=None, alias="ossPdfOfdSize")


class RelatedDocument(BaseModel):
    """A related document (``xgwj``) linked from a detail page."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="bbbs")
    title: str


class HistoricalVersion(BaseModel):
    """A historical version entry from the ``lsyg`` field."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="bbbs")
    title: str
    publish_date: str = Field(alias="gbrq", description="公布日期, e.g. '2020-12-29'")
    highlight: bool = Field(default=False, alias="highLight")


class RelatedMaterial(BaseModel):
    """A related material (``xgzl``) such as 修改决定 or 公告."""

    model_config = ConfigDict(extra="ignore")

    file_id: str = Field(alias="fileId")
    title: str
    title_highlight: str | None = Field(default=None, alias="titleHighLight")
    business_type: str = Field(alias="busiType")
    file_type: str = Field(alias="fileType")
    title_highlight_list: list[dict[str, object]] | None = Field(default=None, alias="titleHightLightList")


class SearchResultRow(BaseModel):
    """A single row from the search/list API response."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="bbbs")
    title: str
    publish_date: str = Field(alias="gbrq", description="公布日期")
    effective_date: str | None = Field(default=None, alias="sxrq", description="施行日期")
    effectiveness: int | None = Field(default=None, alias="sxx", description="时效性 (see Effectiveness)")
    issuing_authority: str = Field(alias="zdjgName", description="制定机关")
    category: str = Field(alias="flxz", description="法律法规分类")
    authority_code_id: int = Field(alias="zdjgCodeId")
    law_code_id: int = Field(alias="flfgCodeId")


class SearchResponse(BaseModel):
    """Top-level response from ``/law-search/search/list``."""

    model_config = ConfigDict(extra="ignore")

    total: int
    rows: list[SearchResultRow]


class DocumentDetail(BaseModel):
    """Full detail from ``/law-search/search/flfgDetails``."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(alias="bbbs")
    title: str
    publish_date: str = Field(alias="gbrq", description="公布日期")
    effective_date: str | None = Field(default=None, alias="sxrq", description="施行日期")
    effectiveness: int | None = Field(default=None, alias="sxx", description="时效性")
    issuing_authority: str = Field(alias="zdjgName", description="制定机关")
    category: str = Field(alias="flxz", description="法律法规分类")
    oss_file: OssFile | None = Field(default=None, alias="ossFile")
    related_documents: list[RelatedDocument] = Field(default_factory=list, alias="xgwj", description="相关文件")
    historical_versions: list[HistoricalVersion] | None = Field(default=None, alias="lsyg", description="历史版本")
    related_materials: list[RelatedMaterial] = Field(default_factory=list, alias="xgzl", description="相关资料")
    content: str | None = None
    repealed_flag: int = Field(default=0, alias="xfFlag")


class DownloadUrl(BaseModel):
    """A single download URL from ``/law-search/download/batch``."""

    model_config = ConfigDict(extra="ignore")

    url: str = Field(description="public OSS URL")
    url_in: str | None = Field(default=None, alias="urlIn", description="internal URL")


class BatchDownloadResponse(BaseModel):
    """Response from ``/law-search/download/batch``."""

    model_config = ConfigDict(extra="ignore")

    msg: str
    code: int
    data: list[DownloadUrl] = Field(default_factory=list)


class MaterialDetail(BaseModel):
    """Detail from ``/law-search/search/xgzlDetails``."""

    model_config = ConfigDict(extra="ignore")

    file_id: str = Field(alias="fileId")
    title: str
    business_type: str | None = Field(default=None, alias="busiType")
    oss_file_path: str | None = Field(default=None, alias="ossFilePath")
    oss_ofd_path: str | None = Field(default=None, alias="ossOfdPath")
    oss_ofd_size: int | None = Field(default=None, alias="ossOfdSize")
    ofd_type: int | None = Field(default=None, alias="ofdType")
