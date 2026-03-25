from typing import Literal
from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    platform: Literal["xiaohongshu", "douyin", "zhihu", "xianyu"] = Field(..., description="平台")
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    max_items: int = Field(default=10, ge=1, le=50, description="最大采集数量")
