from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class CollectStats(BaseModel):
    scanned: int = 0
    parsed: int = 0
    deduplicated: int = 0
    failed: int = 0


class ContentMeta(BaseModel):
    rank: int = 0
    page_no: int = 1
    position: int = 0
    collector: str = "playwright"
    collector_version: str = "v1.0"
    search_url: str = ""
    extracted_from: str = "search_result"


class ContentItem(BaseModel):
    platform: str
    keyword: str
    source_id: str = ""
    source_type: str = "note"

    title: str = ""
    author_name: str = ""
    author_id: str = ""
    author_profile_url: str = ""

    snippet: str = ""
    content_text: str = ""
    content_html: str = ""

    url: str = ""
    cover_url: str = ""
    image_urls: List[str] = Field(default_factory=list)
    video_url: str = ""
    publish_time: str = ""

    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0
    engagement_score: int = 0

    is_ad: bool = False
    is_deleted: bool = False
    lang: str = "zh-CN"
    topic_tags: List[str] = Field(default_factory=list)
    matched_keyword: str = ""

    quality_score: int = 0
    parse_status: Literal["ok", "partial", "failed"] = "partial"
    missing_fields: List[str] = Field(default_factory=list)
    error_message: str = ""

    meta: ContentMeta = Field(default_factory=ContentMeta)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    debug_info: Dict[str, Any] = Field(default_factory=dict)


class CollectResponse(BaseModel):
    success: bool
    platform: str
    keyword: str

    request_id: str
    task_status: Literal["finished", "partial", "failed"]

    count: int
    cost_ms: int
    collected_at: str
    has_more: bool = False
    stats: CollectStats

    items: List[ContentItem]
    message: str = ""
    sample_excel_file: str | None = None
