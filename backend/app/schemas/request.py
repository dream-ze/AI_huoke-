from typing import Literal

from pydantic import BaseModel, Field


class CollectRequest(BaseModel):
    platform: Literal["xiaohongshu", "douyin", "zhihu"] = Field(..., description="平台")
    keyword: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    max_items: int = Field(default=10, ge=1, le=50, description="最大采集数量")
    need_detail: bool = Field(default=True, description="是否补采详情")
    need_comments: bool = Field(default=False, description="是否补采评论数")
    dedup: bool = Field(default=True, description="是否去重")
    timeout_sec: int = Field(default=120, ge=30, le=300, description="采集总超时秒数")
