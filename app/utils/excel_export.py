from datetime import datetime
from pathlib import Path
from typing import List

from openpyxl import Workbook

from app.schemas.result import ContentItem


def export_sample_to_excel(
    items: List[ContentItem],
    keyword: str,
    platform: str,
    sample_size: int,
    export_dir: str,
) -> str:
    """导出采集样例到Excel，返回文件绝对路径。"""
    sample_items = items[:sample_size]

    target_dir = Path(export_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = "".join(ch if ch.isalnum() else "_" for ch in keyword).strip("_")
    if not safe_keyword:
        safe_keyword = "keyword"

    file_name = f"sample_{platform}_{safe_keyword}_{timestamp}.xlsx"
    file_path = target_dir / file_name

    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:
        raise RuntimeError("无法创建Excel工作表")
    sheet.title = "sample_data"

    headers = [
        "platform",
        "keyword",
        "source_id",
        "title",
        "author_name",
        "author_avatar_url",
        "snippet",
        "content_preview",
        "content_text",
        "url",
        "cover_url",
        "content_image_urls",
        "like_count",
        "comment_count",
        "publish_time",
        "engagement_score",
        "quality_score",
        "parse_status",
    ]
    sheet.append(headers)

    for item in sample_items:
        sheet.append(
            [
                item.platform,
                item.keyword,
                item.source_id,
                item.title,
                item.author_name,
                item.author_avatar_url,
                item.snippet,
                item.content_preview,
                item.content_text,
                item.url,
                item.cover_url,
                "\n".join(item.content_image_urls),
                item.like_count,
                item.comment_count,
                item.publish_time,
                item.engagement_score,
                item.quality_score,
                item.parse_status,
            ]
        )

    workbook.save(file_path)
    return str(file_path.resolve())
