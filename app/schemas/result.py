from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    platform: str = Field(..., description="平台")
    keyword: str = ""

    title: str = ""
    author: str = ""

    content: str = ""
    url: str = ""

    cover_url: str = ""

    like_count: Optional[str] = ""
    comment_count: Optional[str] = ""

    publish_time: Optional[str] = ""

    source_id: str = ""

    raw_data: Dict[str, Any] = Field(default_factory=dict)


class CollectResponse(BaseModel):
    success: bool
    platform: str
    keyword: str
    count: int
    items: List[ContentItem]
    message: str = ""
