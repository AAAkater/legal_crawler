"""Related-material API (``/law-search/search/xgzlDetails``).

Fetches detail for a related material (修改决定, 公告, etc.) and
builds the direct OSS download URL for its file.
"""

from legal_crawler.api.client import HttpClient
from legal_crawler.config import config
from legal_crawler.models import MaterialDetail

# OSS bucket base — extracted from batch-download response URLs.
# The batch-download API doesn't support materials, so we construct
# the OSS URL directly from the ``ossFilePath`` returned here.
_OSS_BASE = "https://flkoss.obs-bj2.cucloud.cn"


async def fetch_material_detail(
    client: HttpClient,
    file_id: str,
    bbbs: str,
) -> MaterialDetail:
    """Fetch detail for a related material and return a typed model."""
    raw = await client.get(
        config.material_detail_url,
        {"fileId": file_id, "bbbs": bbbs},
    )

    return MaterialDetail.model_validate(raw["data"])


def build_material_download_url(mat: MaterialDetail) -> str | None:
    """Build a download URL for a material from its OSS path.

    The material detail returns ``ossFilePath`` like
    ``prod/20201229/xxxx.docx``.
    """
    if not mat.oss_file_path:
        return None
    return f"{_OSS_BASE}/{mat.oss_file_path}"


async def download_material_bytes(
    client: HttpClient,
    file_id: str,
    bbbs: str,
) -> tuple[MaterialDetail, bytes] | None:
    """Fetch a material's detail and download its file bytes.

    Returns ``None`` if the material has no downloadable file path.
    """
    mat_detail = await fetch_material_detail(client, file_id, bbbs)

    dl_url = build_material_download_url(mat_detail)
    if dl_url is None:
        return None

    data = await client.get_bytes(dl_url)
    return mat_detail, data
