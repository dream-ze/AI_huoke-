"""
跟进记录模块

包含：
- FollowUpRecord: 跟进记录
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func


class FollowUpRecord(Base):
    """跟进记录"""

    __tablename__ = "follow_up_records"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    follow_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    follow_date = Column(DateTime, nullable=False)
    follow_type = Column(String(20), default="phone")
    content = Column(Text, nullable=False)
    outcome = Column(String(100), nullable=True)
    next_follow_at = Column(DateTime, nullable=True)
    next_action = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = ["FollowUpRecord"]
