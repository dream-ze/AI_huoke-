"""
爆款内容采集分析模块

包含：
- InsightTopic: 主题库
- InsightAuthorProfile: 账号分析档案
- InsightContentItem: 爆款内容条目
- InsightCollectTask: 采集任务记录
- ArkCallLog: Ark API调用日志
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class InsightTopic(Base):
    """主题库 – 征信查询多 / 负债高 / 个体户经营贷 … 每个主题汇聚爆款规律"""

    __tablename__ = "insight_topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    platform_focus = Column(JSON, default=list)  # ["xiaohongshu","douyin"]
    audience_tags = Column(JSON, default=list)  # ["上班族","查询多"]
    common_titles = Column(JSON, default=list)  # 常见标题模板
    common_pain_points = Column(JSON, default=list)  # 常见痛点
    common_structures = Column(JSON, default=list)  # 常见文案结构
    common_ctas = Column(JSON, default=list)  # 常见 CTA
    risk_notes = Column(Text, nullable=True)
    content_count = Column(Integer, default=0)  # 关联内容数（冗余计数）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    content_items = relationship("InsightContentItem", back_populates="topic")
    author_profiles = relationship("InsightAuthorProfile", back_populates="primary_topic")


class InsightAuthorProfile(Base):
    """账号分析档案 – 记录每个平台账号的定位、主题覆盖、风格与爆款率"""

    __tablename__ = "insight_authors"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(32), nullable=False, index=True)
    author_name = Column(String(100), nullable=False)
    author_platform_id = Column(String(200), nullable=True)
    author_profile_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    fans_count = Column(Integer, nullable=True)
    content_count_at_capture = Column(Integer, nullable=True)

    # 分析字段
    account_type = Column(String(32), nullable=True)  # 流量号/专业顾问号/案例号/清单号/避坑号
    account_tags = Column(JSON, default=list)
    topic_coverage = Column(JSON, default=dict)  # {主题名: 内容数}
    style_summary = Column(JSON, default=dict)  # {问题导向:3, 清单导向:5}
    viral_rate = Column(Float, default=0.0)  # 近期爆款率 0-1
    avg_engagement = Column(Float, default=0.0)  # 平均互动分

    primary_topic_id = Column(Integer, ForeignKey("insight_topics.id"), nullable=True)
    primary_topic = relationship("InsightTopic", back_populates="author_profiles")
    content_items = relationship("InsightContentItem", back_populates="author_profile")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InsightContentItem(Base):
    """
    爆款内容标准化条目 – 六类统一字段（平台/账号/内容/互动/分析/风控）
    支持手动录入、批量导入、插件上传三种来源
    """

    __tablename__ = "insight_content_items"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ── 平台基础字段 ──────────────────────────
    platform = Column(String(32), nullable=False, index=True)
    source_type = Column(String(32), default="manual")  # manual / import / plugin
    source_url = Column(String(500), nullable=True)
    collect_time = Column(DateTime, default=datetime.utcnow)
    collect_mode = Column(String(32), default="manual")  # manual / keyword / account / file

    # ── 账号字段 ──────────────────────────────
    author_platform_id = Column(String(200), nullable=True)
    author_name = Column(String(100), nullable=True)
    author_profile_url = Column(String(500), nullable=True)
    fans_count = Column(Integer, nullable=True)
    account_positioning = Column(String(64), nullable=True)
    account_tags = Column(JSON, default=list)
    author_id = Column(Integer, ForeignKey("insight_authors.id"), nullable=True)
    author_profile = relationship("InsightAuthorProfile", back_populates="content_items")

    # ── 内容字段 ──────────────────────────────
    content_platform_id = Column(String(200), nullable=True)
    content_type = Column(String(32), default="post")  # post / video / article
    title = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    content_summary = Column(Text, nullable=True)
    publish_time = Column(DateTime, nullable=True)
    raw_payload = Column(JSON, nullable=True)  # 原始采集数据存档
    manual_note = Column(Text, nullable=True)

    # ── 互动字段 ──────────────────────────────
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    follower_count_at_capture = Column(Integer, nullable=True)
    engagement_score = Column(Float, default=0.0)  # 系统计算互动分
    is_hot = Column(Boolean, default=False)
    heat_tier = Column(String(16), default="normal")  # normal / warm / hot / viral

    # ── AI 分析字段 ────────────────────────────
    topic_id = Column(Integer, ForeignKey("insight_topics.id"), nullable=True, index=True)
    topic = relationship("InsightTopic", back_populates="content_items")
    audience_tags = Column(JSON, default=list)
    structure_type = Column(String(64), nullable=True)  # 问题-原因-建议
    hook_type = Column(String(64), nullable=True)  # 问题开头/数字开头/故事引入
    tone_style = Column(String(64), nullable=True)  # 自然口语风/专业建议风
    cta_type = Column(String(64), nullable=True)  # 评论引导/私信引导/关注引导
    emotion_level = Column(Integer, default=3)  # 1-5
    info_density = Column(Integer, default=3)  # 1-5
    title_formula = Column(String(200), nullable=True)
    pain_points = Column(JSON, default=list)
    highlights = Column(JSON, default=list)  # 爆点摘要
    ai_analysis = Column(JSON, default=dict)  # 完整 AI 分析原文
    ai_analyzed = Column(Boolean, default=False)

    # ── 风控字段 ──────────────────────────────
    risk_level = Column(String(16), default="low")
    risk_flags = Column(JSON, default=list)
    rule_version = Column(String(32), nullable=True)
    compliance_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")


class InsightCollectTask(Base):
    """采集任务记录 – 统一调度层，支持按账号/关键词/主题/链接/文件多种模式"""

    __tablename__ = "insight_collect_tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String(32), nullable=False)
    collect_mode = Column(String(32), nullable=False)  # by_account/by_keyword/by_topic/link_import/file_import
    target_value = Column(String(500), nullable=True)  # 账号名/关键词/主题名
    time_range = Column(String(64), nullable=True)
    status = Column(String(32), default="pending")  # pending/running/done/failed
    result_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    run_at = Column(DateTime, nullable=True)

    owner = relationship("User")


class ArkCallLog(Base):
    """Ark API call log for observability and analytics"""

    __tablename__ = "ark_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    scene = Column(String(64), nullable=False, default="general")
    provider = Column(String(32), nullable=False, default="ark")
    model = Column(String(128), nullable=False)
    endpoint = Column(String(255), nullable=False, default="/responses")

    success = Column(Boolean, default=True, nullable=False)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)

    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="ark_call_logs")


__all__ = [
    "InsightTopic",
    "InsightAuthorProfile",
    "InsightContentItem",
    "InsightCollectTask",
    "ArkCallLog",
]
