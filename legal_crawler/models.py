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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Effectiveness(IntEnum):
    """Time-effectiveness status codes from the API ``sxx`` field."""

    REPEALED = 1  # 已废止
    MODIFIED = 2  # 已修改
    EFFECTIVE = 3  # 有效
    # NOTE: ``None`` means the item is a 修改、废止的决定 (no status code).


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

    bbbs: str
    title: str


class HistoricalVersion(BaseModel):
    """A historical version entry from the ``lsyg`` field."""

    model_config = ConfigDict(extra="ignore")

    bbbs: str
    title: str
    gbrq: str  # 公布日期, e.g. "2020-12-29"
    highlight: bool = Field(default=False, alias="highLight")


class RelatedMaterial(BaseModel):
    """A related material (``xgzl``) such as 修改决定 or 公告."""

    model_config = ConfigDict(extra="ignore")

    file_id: str = Field(alias="fileId")
    title: str
    title_highlight: str | None = Field(default=None, alias="titleHighLight")
    busi_type: str = Field(alias="busiType")
    file_type: str = Field(alias="fileType")
    title_highlight_list: list[dict[str, Any]] | None = Field(default=None, alias="titleHightLightList")


class SearchResultRow(BaseModel):
    """A single row from the search/list API response."""

    model_config = ConfigDict(extra="ignore")

    bbbs: str
    title: str
    gbrq: str  # 公布日期
    sxrq: str | None = None  # 施行日期
    sxx: int | None = None  # 时效性 (see Effectiveness)
    zdjg_name: str = Field(alias="zdjgName")  # 制定机关
    flxz: str  # 法律法规分类
    zdjg_code_id: int = Field(alias="zdjgCodeId")
    flfg_code_id: int = Field(alias="flfgCodeId")


class SearchResponse(BaseModel):
    """Top-level response from ``/law-search/search/list``."""

    model_config = ConfigDict(extra="ignore")

    total: int
    rows: list[SearchResultRow]


class DocumentDetail(BaseModel):
    """Full detail from ``/law-search/search/flfgDetails``."""

    model_config = ConfigDict(extra="ignore")

    bbbs: str
    title: str
    gbrq: str  # 公布日期
    sxrq: str | None = None  # 施行日期
    sxx: int | None = None  # 时效性
    zdjg_name: str = Field(alias="zdjgName")
    flxz: str  # 法律法规分类
    oss_file: OssFile | None = Field(default=None, alias="ossFile")
    xgwj: list[RelatedDocument] = Field(default_factory=list)  # 相关文件
    lsyg: list[HistoricalVersion] | None = None  # 历史版本
    xgzl: list[RelatedMaterial] = Field(default_factory=list)  # 相关资料
    content: str | None = None
    xf_flag: int = Field(default=0, alias="xfFlag")


class DownloadUrl(BaseModel):
    """A single download URL from ``/law-search/download/batch``."""

    model_config = ConfigDict(extra="ignore")

    url: str  # public OSS URL
    url_in: str | None = Field(default=None, alias="urlIn")  # internal URL


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
    busi_type: str | None = Field(default=None, alias="busiType")
    oss_file_path: str | None = Field(default=None, alias="ossFilePath")
    oss_ofd_path: str | None = Field(default=None, alias="ossOfdPath")
    oss_ofd_size: int | None = Field(default=None, alias="ossOfdSize")
    ofd_type: int | None = Field(default=None, alias="ofdType")
