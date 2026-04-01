from typing import Any, Dict, Literal, Optional

from app.schemas.result import ContentItem
from pydantic import BaseModel, Field, model_validator

PlatformType = Literal["xiaohongshu", "douyin", "zhihu"]


class CollectDetailRequest(BaseModel):
    platform: PlatformType
    url: Optional[str] = None
    source_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_url_or_source_id(self):
        if not self.url and not self.source_id:
            raise ValueError("url 和 source_id 至少要传一个")
        return self


class CollectDetailResponse(BaseModel):
    success: bool
    platform: str
    url: str = ""
    source_id: str = ""
    data: Optional[ContentItem] = None
    message: str = ""
    raw_data: Dict[str, Any] = Field(default_factory=dict)
