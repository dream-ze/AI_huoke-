"""
线索归因模块

包含：
- LeadSourceAttribution: 线索来源归因
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func


class LeadSourceAttribution(Base):
    """线索来源归因"""

    __tablename__ = "lead_source_attributions"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    publish_account_id = Column(Integer, ForeignKey("publish_accounts.id"), nullable=True)
    published_content_id = Column(Integer, ForeignKey("published_contents.id"), nullable=True)
    generation_task_id = Column(Integer, nullable=True)
    touchpoint_platform = Column(String(50), nullable=True)
    touchpoint_url = Column(String(1000), nullable=True)
    first_touch_time = Column(DateTime, nullable=True)
    last_touch_time = Column(DateTime, nullable=True)
    conversion_path = Column(JSON, nullable=True)
    attribution_type = Column(String(20), default="last_touch")
    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = ["LeadSourceAttribution"]
