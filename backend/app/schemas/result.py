from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ParseStage = Literal["list", "detail"]
ParseStatus = Literal["list_only", "detail_success", "detail_failed", "dropped"]
RiskLevel = Literal["low", "medium", "high"]


class CollectStats(BaseModel):
    discovered: int = 0
    list_success: int = 0
    detail_attempted: int = 0
    detail_success: int = 0
    detail_failed: int = 0
    dropped: int = 0


class ContentItem(BaseModel):
    source_platform: str
    source_type: str = "note"
    source_id: str = ""
    url: str = ""
    keyword: str = ""
    task_id: str = ""

    title: str | None = None
    snippet: str | None = None
    cover_url: str | None = None
    author_name: str | None = None
    author_id: str | None = None
    author_home_url: str | None = None
    like_count: int | None = None

    content_text: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    image_count: int = 0
    publish_time: str | None = None
    comment_count: int | None = None
    share_count: int | None = None
    collect_count: int | None = None
    tags: list[str] = Field(default_factory=list)

    parse_stage: ParseStage = "list"
    parse_status: ParseStatus = "list_only"
    detail_attempted: bool = False
    detail_error: str = ""
    drop_reason: str = ""
    field_completeness: float = 0.0

    engagement_score: float = 0.0
    quality_score: float = 0.0
    lead_score: float = 0.0
    risk_level: RiskLevel = "low"
    risk_reason: str = ""
    has_contact_hint: bool = False
    content_length: int = 0
    is_detail_complete: bool = False

    collected_at: datetime
    updated_at: datetime

    raw_data: dict[str, Any] = Field(default_factory=dict)


class CollectResponse(BaseModel):
    success: bool
    platform: str
    keyword: str
    task_id: str
    count: int
    items: list[ContentItem]
    stats: CollectStats
    message: str = ""
    request_id: str
    cost_ms: int
    collected_at: datetime
