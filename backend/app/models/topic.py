"""
选题计划与引流策略模块

包含：
- TopicPlan: 选题计划
- TopicIdea: 选题创意
- HotTopic: 热门话题
- TrafficStrategy: 引流策略
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class TopicPlan(Base):
    """选题计划"""

    __tablename__ = "topic_plans"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=True)  # xiaohongshu/douyin/zhihu
    audience = Column(String(100), nullable=True)  # 目标人群
    status = Column(String(20), default="draft")  # draft/scheduled/published/archived
    scheduled_date = Column(Date, nullable=True)  # 计划发布日期
    content_direction = Column(Text, nullable=True)  # 内容方向描述
    reference_materials = Column(JSON, nullable=True)  # 参考素材ID列表
    tags = Column(JSON, nullable=True)  # 标签列表
    notes = Column(Text, nullable=True)  # 备注
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    ideas = relationship("TopicIdea", back_populates="plan", cascade="all, delete-orphan")


class TopicIdea(Base):
    """选题创意/灵感"""

    __tablename__ = "topic_ideas"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("topic_plans.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # 关键词列表
    estimated_engagement = Column(String(20), nullable=True)  # low/medium/high
    source = Column(String(50), default="manual")  # manual/ai_recommend/hot_trend
    status = Column(String(20), default="pending")  # pending/accepted/rejected/used
    platform = Column(String(50), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    plan = relationship("TopicPlan", back_populates="ideas")


class HotTopic(Base):
    """热门话题追踪"""

    __tablename__ = "hot_topics"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # xiaohongshu/douyin/zhihu
    title = Column(String(300), nullable=False)
    heat_score = Column(Float, default=0.0)  # 热度分数
    trend_direction = Column(String(20), default="stable")  # up/down/stable
    category = Column(String(100), nullable=True)  # 话题分类
    source_url = Column(String(500), nullable=True)  # 来源链接
    discovered_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # 热度过期时间

    __table_args__ = (
        Index("idx_hot_topic_platform_heat", "platform", "heat_score"),
        Index("idx_hot_topic_discovered", "discovered_at"),
    )


class TrafficStrategy(Base):
    """引流策略"""

    __tablename__ = "traffic_strategies"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)  # xiaohongshu/douyin/zhihu
    strategy_type = Column(String(50), nullable=False)  # cta/comment_guide/profile_link/live_stream/group
    target_audience = Column(String(200), nullable=True)
    cta_template = Column(Text, nullable=True)  # CTA话术模板
    budget = Column(Float, nullable=True)  # 预算（元）
    performance_metrics = Column(JSON, nullable=True)  # {views, clicks, leads, conversions, cost_per_lead}
    status = Column(String(20), default="active")  # active/paused/archived
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_traffic_owner_platform", "owner_id", "platform"),
        Index("idx_traffic_status", "status"),
    )


__all__ = ["TopicPlan", "TopicIdea", "HotTopic", "TrafficStrategy"]
