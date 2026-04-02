"""
发布内容模块

包含：
- PublishedContent: 已发布内容
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func


class PublishedContent(Base):
    """已发布内容"""

    __tablename__ = "published_contents"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    generation_result_id = Column(Integer, ForeignKey("mvp_generation_results.id"), nullable=True)
    publish_account_id = Column(Integer, ForeignKey("publish_accounts.id"), nullable=True)
    title = Column(String(500), nullable=True)
    content_text = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    publish_time = Column(DateTime, nullable=True)
    post_url = Column(String(1000), nullable=True)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    wechat_adds = Column(Integer, default=0)
    leads_count = Column(Integer, default=0)
    tracking_code = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["PublishedContent"]
