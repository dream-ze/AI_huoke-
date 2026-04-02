"""
营销活动模块

包含：
- Campaign: 营销活动
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func


class Campaign(Base):
    """营销活动"""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    target_audience = Column(String(200), nullable=True)
    target_platform = Column(String(50), nullable=True)
    objective = Column(String(100), nullable=True)
    status = Column(String(20), default="draft")
    budget = Column(Numeric(15, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = ["Campaign"]
