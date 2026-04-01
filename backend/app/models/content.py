"""
内容资产管理模块

包含：
- ContentAsset: 内容资产主表
- ContentBlock: 内容结构化块
- ContentComment: 内容评论
- ContentSnapshot: 页面快照
- ContentInsight: 内容洞察分析
- RewrittenContent: 改写内容
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class ContentAsset(Base):
    """Content asset collected from platforms"""

    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(32), nullable=False)
    source_url = Column(String(500), nullable=True)
    content_type = Column(String(32), nullable=False)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=True)
    publish_time = Column(DateTime, nullable=True)

    tags = Column(JSON, default=list)  # List of tags
    comments_keywords = Column(JSON, default=list)  # Extracted comment keywords
    top_comments = Column(JSON, default=list)  # Top 20 comments

    metrics = Column(JSON, default=dict)  # {likes, comments, favorites, shares}
    heat_score = Column(Float, default=0.0)  # Calculated heat score
    is_viral = Column(Boolean, default=False)  # Is this viral content?

    source_type = Column(String(32), default="paste")  # link | paste | import
    category = Column(String(64), nullable=True)  # domain category (e.g. 额度提升, 客户话术)

    manual_note = Column(Text, nullable=True)
    screenshots = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="contents")
    rewrites = relationship("RewrittenContent", back_populates="source_content")
    blocks = relationship("ContentBlock", back_populates="content", cascade="all,delete-orphan")
    comments = relationship("ContentComment", back_populates="content", cascade="all,delete-orphan")
    snapshots = relationship("ContentSnapshot", back_populates="content", cascade="all,delete-orphan")
    insights = relationship("ContentInsight", back_populates="content", cascade="all,delete-orphan")


class ContentBlock(Base):
    """Structured body blocks for a collected content item."""

    __tablename__ = "content_blocks"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    block_type = Column(String(32), nullable=False, default="paragraph")
    block_order = Column(Integer, nullable=False, default=0)
    block_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("ContentAsset", back_populates="blocks")


class ContentComment(Base):
    """Structured comments for a collected content item."""

    __tablename__ = "content_comments"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(Integer, ForeignKey("content_comments.id", ondelete="SET NULL"), nullable=True)
    commenter_name = Column(String(100), nullable=True)
    comment_text = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("ContentAsset", back_populates="comments")


class ContentSnapshot(Base):
    """Page snapshots captured at collect time."""

    __tablename__ = "content_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_html = Column(Text, nullable=True)
    screenshot_url = Column(String(500), nullable=True)
    page_meta_json = Column(JSON, default=dict)
    collected_at = Column(DateTime, default=datetime.utcnow)

    content = relationship("ContentAsset", back_populates="snapshots")


class ContentInsight(Base):
    """Asynchronous insight results for a content item."""

    __tablename__ = "content_insights"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    high_freq_questions_json = Column(JSON, default=list)
    key_sentences_json = Column(JSON, default=list)
    title_pattern = Column(String(128), nullable=True)
    suggested_topics_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    content = relationship("ContentAsset", back_populates="insights")


class RewrittenContent(Base):
    """Rewritten content in different styles"""

    __tablename__ = "rewritten_contents"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("content_assets.id"), nullable=False)

    target_platform = Column(String(32), nullable=False)
    content_type = Column(String(32), nullable=False)  # xiaohongshu, douyin, zhihu, etc.

    original_content = Column(Text, nullable=False)
    rewritten_content = Column(Text, nullable=False)

    risk_level = Column(String(16), default="low")
    compliance_score = Column(Float, default=0.0)  # 0-100
    compliance_status = Column(String(32), default="pending")  # pending, passed, failed

    risk_points = Column(JSON, default=list)  # List of risk points
    suggestions = Column(JSON, default=list)  # Suggestions for improvement

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_content = relationship("ContentAsset", back_populates="rewrites")
    publish_records = relationship("PublishRecord", back_populates="content")


__all__ = [
    "ContentAsset",
    "ContentBlock",
    "ContentComment",
    "ContentSnapshot",
    "ContentInsight",
    "RewrittenContent",
]
