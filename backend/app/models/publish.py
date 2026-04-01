"""
发布管理模块

包含：
- PublishRecord: 发布记录
- PublishTask: 发布任务
- PublishTaskFeedback: 发布任务反馈
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class PublishRecord(Base):
    """Content publish record"""

    __tablename__ = "publish_records"

    id = Column(Integer, primary_key=True, index=True)
    rewritten_content_id = Column(Integer, ForeignKey("rewritten_contents.id"), nullable=False)

    platform = Column(String(32), nullable=False)
    account_name = Column(String(128), nullable=False)
    publish_time = Column(DateTime, default=datetime.utcnow)
    published_by = Column(String(100), nullable=True)

    # Performance metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    private_messages = Column(Integer, default=0)

    # Conversion metrics
    wechat_adds = Column(Integer, default=0)
    leads = Column(Integer, default=0)
    valid_leads = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    content = relationship("RewrittenContent", back_populates="publish_records")


class PublishTask(Base):
    """Publish task workflow entity."""

    __tablename__ = "publish_tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rewritten_content_id = Column(Integer, ForeignKey("rewritten_contents.id"), nullable=True)
    publish_record_id = Column(Integer, ForeignKey("publish_records.id"), nullable=True)

    platform = Column(String(32), nullable=False)
    account_name = Column(String(128), nullable=False)
    task_title = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)

    status = Column(String(32), default="pending")  # pending, claimed, submitted, rejected, closed
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_time = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    post_url = Column(String(500), nullable=True)
    reject_reason = Column(Text, nullable=True)
    close_reason = Column(Text, nullable=True)

    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    private_messages = Column(Integer, default=0)
    wechat_adds = Column(Integer, default=0)
    leads = Column(Integer, default=0)
    valid_leads = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rewritten_content = relationship("RewrittenContent", foreign_keys=[rewritten_content_id])
    publish_record = relationship("PublishRecord", foreign_keys=[publish_record_id])
    feedbacks = relationship("PublishTaskFeedback", back_populates="task", cascade="all,delete-orphan")


class PublishTaskFeedback(Base):
    """Publish task action log and feedback."""

    __tablename__ = "publish_task_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("publish_tasks.id"), nullable=False, index=True)
    action = Column(String(32), nullable=False)  # create, claim, submit, reject, close
    note = Column(Text, nullable=True)
    payload = Column(JSON, default=dict)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("PublishTask", back_populates="feedbacks")


__all__ = ["PublishRecord", "PublishTask", "PublishTaskFeedback"]
