"""
发布账号模块

包含：
- PublishAccount: 发布账号
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func


class PublishAccount(Base):
    """发布账号"""

    __tablename__ = "publish_accounts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    platform = Column(String(50), nullable=False)
    account_name = Column(String(200), nullable=False)
    account_id = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    follower_count = Column(Integer, default=0)
    risk_level = Column(String(20), default="low")
    status = Column(String(20), default="active")
    daily_post_limit = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["PublishAccount"]
