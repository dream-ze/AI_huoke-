"""
采集管理模块

包含：
- BrowserPluginCollection: 浏览器插件采集
- InboxItem: 收件箱条目
- CollectTask: 采集任务
- EmployeeLinkSubmission: 员工链接提交
- MaterialInbox: 素材收件箱
- SourceContent: 原始内容
- NormalizedContent: 标准化内容
- MaterialItem: 素材条目
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class BrowserPluginCollection(Base):
    """Content collected via browser plugin"""

    __tablename__ = "plugin_collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    platform = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    author = Column(String(100), nullable=True)
    publish_time = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    comments_json = Column(JSON, default=list)
    url = Column(String(500), nullable=False)

    heat_score = Column(Float, default=0.0)
    is_viral = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class InboxItem(Base):
    """Collected content waiting in inbox before being promoted to material library."""

    __tablename__ = "inbox_items"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String(32), nullable=False)
    source_url = Column(String(500), nullable=True)
    content_type = Column(String(32), nullable=False, default="post")

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    publish_time = Column(DateTime, nullable=True)

    tags = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    source_type = Column(String(32), default="paste")
    category = Column(String(64), nullable=True)
    manual_note = Column(Text, nullable=True)

    heat_score = Column(Float, default=0.0)
    is_viral = Column(Boolean, default=False)
    status = Column(String(32), default="pending")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    promoted_content_id = Column(Integer, ForeignKey("content_assets.id"), nullable=True)
    promoted_insight_item_id = Column(Integer, ForeignKey("insight_content_items.id"), nullable=True)
    review_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    promoted_content = relationship("ContentAsset", foreign_keys=[promoted_content_id])
    promoted_insight_item = relationship("InsightContentItem", foreign_keys=[promoted_insight_item_id])


class CollectTask(Base):
    """Keyword based browser collection task."""

    __tablename__ = "collect_tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String(30), nullable=False, default="keyword")
    platform = Column(String(30), nullable=False)
    keyword = Column(String(255), nullable=False)
    max_items = Column(Integer, nullable=False, default=20)

    status = Column(String(20), nullable=False, default="pending")
    result_count = Column(Integer, nullable=False, default=0)
    inserted_count = Column(Integer, nullable=False, default=0)
    review_count = Column(Integer, nullable=False, default=0)
    discard_count = Column(Integer, nullable=False, default=0)
    duplicate_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeLinkSubmission(Base):
    """Employee/manual/wechat link submissions before parsing."""

    __tablename__ = "employee_link_submissions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source_type = Column(String(30), nullable=False)  # manual_link / wechat_robot
    platform = Column(String(30), nullable=True)
    url = Column(String(500), nullable=False)
    note = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MaterialInbox(Base):
    """Unified intake inbox for all external content inputs."""

    __tablename__ = "material_inbox"
    __table_args__ = (
        UniqueConstraint("owner_id", "platform", "source_id", name="uq_material_inbox_owner_platform_source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_channel = Column(
        String(30), nullable=False
    )  # collect_task / employee_submission / wechat_robot / manual_input
    source_task_id = Column(Integer, ForeignKey("collect_tasks.id"), nullable=True, index=True)
    source_submission_id = Column(Integer, ForeignKey("employee_link_submissions.id"), nullable=True, index=True)

    platform = Column(String(30), nullable=False)
    source_id = Column(String(255), nullable=True, index=True)
    keyword = Column(String(255), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    cover_url = Column(String(500), nullable=True)

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    publish_time = Column(DateTime, nullable=True)

    parse_status = Column(String(32), nullable=False, default="success", index=True)
    risk_status = Column(String(32), nullable=False, default="safe", index=True)
    quality_score = Column(Integer, nullable=False, default=0)
    relevance_score = Column(Integer, nullable=False, default=0)
    lead_score = Column(Integer, nullable=False, default=0)
    is_duplicate = Column(Boolean, nullable=False, default=False, index=True)
    filter_reason = Column(Text, nullable=True)

    raw_data = Column(JSON, default=dict)

    status = Column(String(20), nullable=False, default="pending", index=True)  # pending / review / discard
    submitted_by_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    remark = Column(Text, nullable=True)
    review_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceContent(Base):
    """Raw content inputs from collector or manual submissions."""

    __tablename__ = "source_contents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_channel = Column(String(30), nullable=False, default="manual_input", index=True)
    source_task_id = Column(Integer, ForeignKey("collect_tasks.id"), nullable=True, index=True)
    source_submission_id = Column(Integer, ForeignKey("employee_link_submissions.id"), nullable=True, index=True)
    submitted_by_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    source_type = Column(String(20), nullable=False, default="manual")
    source_platform = Column(String(50), nullable=False, index=True)
    source_id = Column(String(128), nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    keyword = Column(String(255), nullable=True, index=True)

    raw_title = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    raw_payload = Column(JSON, default=dict)

    author_name = Column(String(255), nullable=True)
    cover_url = Column(String(500), nullable=True)
    publish_time = Column(DateTime, nullable=True)

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    parse_status = Column(String(32), nullable=False, default="success")
    risk_status = Column(String(32), nullable=False, default="safe")
    remark = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    normalized_contents = relationship(
        "NormalizedContent", back_populates="source_content", cascade="all,delete-orphan"
    )


class NormalizedContent(Base):
    """Cleaned and standardized content payloads."""

    __tablename__ = "normalized_contents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_content_id = Column(
        Integer, ForeignKey("source_contents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=False, index=True)

    platform = Column(String(50), nullable=False, index=True)
    source_id = Column(String(128), nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    cover_url = Column(String(500), nullable=True)
    publish_time = Column(DateTime, nullable=True)

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    parse_status = Column(String(32), nullable=False, default="success")
    risk_status = Column(String(32), nullable=False, default="safe")
    keyword = Column(String(255), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    source_content = relationship("SourceContent", back_populates="normalized_contents")
    material_items = relationship("MaterialItem", back_populates="normalized_content", cascade="all,delete-orphan")


class MaterialItem(Base):
    """Primary asset table. Inbox is only a filtered view of this table."""

    __tablename__ = "material_items"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    source_channel = Column(String(30), nullable=False, default="manual_input", index=True)
    source_task_id = Column(Integer, ForeignKey("collect_tasks.id"), nullable=True, index=True)
    source_submission_id = Column(Integer, ForeignKey("employee_link_submissions.id"), nullable=True, index=True)
    submitted_by_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    source_content_id = Column(
        Integer, ForeignKey("source_contents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    normalized_content_id = Column(
        Integer, ForeignKey("normalized_contents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    platform = Column(String(50), nullable=False, index=True)
    source_id = Column(String(128), nullable=True, index=True)
    source_url = Column(Text, nullable=True)
    keyword = Column(String(255), nullable=True, index=True)

    title = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    content_preview = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    cover_url = Column(String(500), nullable=True)
    publish_time = Column(DateTime, nullable=True)

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    hot_level = Column(String(10), nullable=False, default="low")
    lead_level = Column(String(10), nullable=False, default="low")
    lead_reason = Column(Text, nullable=True)
    quality_score = Column(Integer, nullable=False, default=0)
    relevance_score = Column(Integer, nullable=False, default=0)
    lead_score = Column(Integer, nullable=False, default=0)

    parse_status = Column(String(32), nullable=False, default="success", index=True)
    risk_status = Column(String(32), nullable=False, default="safe", index=True)
    is_duplicate = Column(Boolean, nullable=False, default=False, index=True)
    filter_reason = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default="pending", index=True)
    remark = Column(Text, nullable=True)
    review_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_content = relationship("SourceContent", foreign_keys=[source_content_id])
    normalized_content = relationship("NormalizedContent", back_populates="material_items")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="material_item", cascade="all,delete-orphan")
    generation_tasks = relationship("GenerationTask", back_populates="material_item", cascade="all,delete-orphan")


__all__ = [
    "BrowserPluginCollection",
    "InboxItem",
    "CollectTask",
    "EmployeeLinkSubmission",
    "MaterialInbox",
    "SourceContent",
    "NormalizedContent",
    "MaterialItem",
]
