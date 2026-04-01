"""
枚举类型定义模块

包含所有模型使用的枚举类型
"""

import enum


class PlatformType(str, enum.Enum):
    """平台类型"""

    xiaohongshu = "xiaohongshu"
    douyin = "douyin"
    zhihu = "zhihu"
    xianyu = "xianyu"
    wechat = "wechat"
    other = "other"


class ContentType(str, enum.Enum):
    """内容类型"""

    post = "post"
    video = "video"
    answer = "answer"
    listing = "listing"


class RiskLevel(str, enum.Enum):
    """风险等级"""

    low = "low"
    medium = "medium"
    high = "high"


class IntentionLevel(str, enum.Enum):
    """意向等级"""

    low = "low"
    medium = "medium"
    high = "high"


class CustomerStatus(str, enum.Enum):
    """客户状态"""

    new = "new"
    contacted = "contacted"
    pending_follow = "pending_follow"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"


__all__ = [
    "PlatformType",
    "ContentType",
    "RiskLevel",
    "IntentionLevel",
    "CustomerStatus",
]
