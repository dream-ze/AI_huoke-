from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ParseStatus = Literal[
    "list_only",
    "detail_success",
    "detail_failed",
    "parse_failed",
    "risk_blocked",
]

RiskStatus = Literal["normal", "login_required", "captcha", "blocked"]


class CollectStats(BaseModel):
    discovered: int = 0
    detail_attempted: int = 0
    detail_success: int = 0
    parse_failed: int = 0
    risk_blocked: int = 0
    deduplicated: int = 0


class ContentItem(BaseModel):
    platform: str
    keyword: str | None = None

    source_id: str
    url: str

    title: str | None = None
    author_name: str | None = None
    author_id: str | None = None
    author_avatar_url: str | None = None

    snippet: str | None = None
    content_text: str | None = None
    content_preview: str | None = None

    cover_url: str | None = None
    content_image_urls: list[str] = Field(default_factory=list)

    like_count: int | None = None
    comment_count: int | None = None

    publish_time: datetime | None = None
    collected_at: datetime

    parse_status: ParseStatus
    risk_status: RiskStatus | None = None

    engagement_score: float | None = None
    quality_score: float | None = None

    field_source: dict[str, str] = Field(default_factory=dict)
    data_quality: dict[str, Any] = Field(default_factory=dict)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class CollectResponse(BaseModel):
    success: bool
    platform: str
    keyword: str
    count: int
    items: list[ContentItem]
    stats: CollectStats
    message: str = ""
    request_id: str
    cost_ms: int
    collected_at: datetime
