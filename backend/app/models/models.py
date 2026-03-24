from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default="operator", nullable=False)
    is_active = Column(Boolean, default=True)
    wecom_userid = Column(String(64), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contents = relationship("ContentAsset", back_populates="owner")
    leads = relationship("Lead", back_populates="owner")
    customers = relationship("Customer", back_populates="owner")
    ark_call_logs = relationship("ArkCallLog", back_populates="user")


class PlatformType(str, enum.Enum):
    xiaohongshu = "xiaohongshu"
    douyin = "douyin"
    zhihu = "zhihu"
    xianyu = "xianyu"
    wechat = "wechat"
    other = "other"


class ContentType(str, enum.Enum):
    post = "post"
    video = "video"
    answer = "answer"
    listing = "listing"


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


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


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


class IntentionLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class CustomerStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    pending_follow = "pending_follow"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"


class Lead(Base):
    """Lead pool entity generated from publish tasks and manual operations."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    publish_task_id = Column(Integer, ForeignKey("publish_tasks.id"), nullable=True, index=True)

    platform = Column(String(32), nullable=False)
    source = Column(String(32), default="publish_task")
    title = Column(String(255), nullable=False)
    post_url = Column(String(500), nullable=True)

    wechat_adds = Column(Integer, default=0)
    leads = Column(Integer, default=0)
    valid_leads = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    status = Column(String(32), default="new")  # new, contacted, qualified, converted, lost
    intention_level = Column(String(16), default="medium")
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="leads")
    publish_task = relationship("PublishTask", foreign_keys=[publish_task_id])
    customer = relationship("Customer", back_populates="lead", uselist=False)


class Customer(Base):
    """Customer contact information"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    nickname = Column(String(100), nullable=False)
    wechat_id = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    
    source_platform = Column(String(32), nullable=False)
    source_content_id = Column(Integer, nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, unique=True)
    
    tags = Column(JSON, default=list)
    intention_level = Column(String(16), default="medium")  # low, medium, high
    customer_status = Column(String(32), default="new")
    
    inquiry_content = Column(Text, nullable=True)
    follow_records = Column(JSON, default=list)  # [{date, content, owner}, ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customers")
    lead = relationship("Lead", back_populates="customer")


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


# ─────────────────────────────────────────────────────────────
# 爆款内容采集分析中心 模型
# ─────────────────────────────────────────────────────────────

class InsightTopic(Base):
    """主题库 – 征信查询多 / 负债高 / 个体户经营贷 … 每个主题汇聚爆款规律"""
    __tablename__ = "insight_topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    platform_focus = Column(JSON, default=list)     # ["xiaohongshu","douyin"]
    audience_tags = Column(JSON, default=list)       # ["上班族","查询多"]
    common_titles = Column(JSON, default=list)       # 常见标题模板
    common_pain_points = Column(JSON, default=list)  # 常见痛点
    common_structures = Column(JSON, default=list)   # 常见文案结构
    common_ctas = Column(JSON, default=list)         # 常见 CTA
    risk_notes = Column(Text, nullable=True)
    content_count = Column(Integer, default=0)       # 关联内容数（冗余计数）
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
    topic_coverage = Column(JSON, default=dict)   # {主题名: 内容数}
    style_summary = Column(JSON, default=dict)    # {问题导向:3, 清单导向:5}
    viral_rate = Column(Float, default=0.0)       # 近期爆款率 0-1
    avg_engagement = Column(Float, default=0.0)   # 平均互动分

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
    source_type = Column(String(32), default="manual")   # manual / import / plugin
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
    content_type = Column(String(32), default="post")    # post / video / article
    title = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    content_summary = Column(Text, nullable=True)
    publish_time = Column(DateTime, nullable=True)
    raw_payload = Column(JSON, nullable=True)            # 原始采集数据存档
    manual_note = Column(Text, nullable=True)

    # ── 互动字段 ──────────────────────────────
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    follower_count_at_capture = Column(Integer, nullable=True)
    engagement_score = Column(Float, default=0.0)        # 系统计算互动分
    is_hot = Column(Boolean, default=False)
    heat_tier = Column(String(16), default="normal")     # normal / warm / hot / viral

    # ── AI 分析字段 ────────────────────────────
    topic_id = Column(Integer, ForeignKey("insight_topics.id"), nullable=True, index=True)
    topic = relationship("InsightTopic", back_populates="content_items")
    audience_tags = Column(JSON, default=list)
    structure_type = Column(String(64), nullable=True)   # 问题-原因-建议
    hook_type = Column(String(64), nullable=True)        # 问题开头/数字开头/故事引入
    tone_style = Column(String(64), nullable=True)       # 自然口语风/专业建议风
    cta_type = Column(String(64), nullable=True)         # 评论引导/私信引导/关注引导
    emotion_level = Column(Integer, default=3)           # 1-5
    info_density = Column(Integer, default=3)            # 1-5
    title_formula = Column(String(200), nullable=True)
    pain_points = Column(JSON, default=list)
    highlights = Column(JSON, default=list)              # 爆点摘要
    ai_analysis = Column(JSON, default=dict)             # 完整 AI 分析原文
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
    status = Column(String(32), default="pending")     # pending/running/done/failed
    result_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    run_at = Column(DateTime, nullable=True)

    owner = relationship("User")


class RewritePerformance(Base):
    """改写效果追踪 – 记录每次改写的版本、风格及发布后的真实效果"""
    __tablename__ = "rewrite_performance"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_content_id = Column(Integer, ForeignKey("content_assets.id"), nullable=True, index=True)

    platform = Column(String(32), nullable=False)
    rewrite_style = Column(String(64), nullable=True)   # aggressive/mild/professional/casual/…
    rewritten_content = Column(Text, nullable=False)

    # 预测分数（改写时由 AI 给出）
    predicted_engagement = Column(Float, nullable=True)
    predicted_conversion = Column(Float, nullable=True)

    # 发布后真实数据回流
    actual_views = Column(Integer, nullable=True)
    actual_likes = Column(Integer, nullable=True)
    actual_comments = Column(Integer, nullable=True)
    actual_shares = Column(Integer, nullable=True)
    actual_conversions = Column(Integer, nullable=True)

    # 综合效果评分（可由后台计算填入）
    effectiveness_score = Column(Float, nullable=True)

    publish_metrics = Column(JSON, default=dict)        # 原始发布数据
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")
    source_content = relationship("ContentAsset")


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
