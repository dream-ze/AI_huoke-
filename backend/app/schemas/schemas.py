from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== Auth Schemas =====
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ===== Content Asset Schemas =====
class ContentAssetCreate(BaseModel):
    platform: str
    source_url: Optional[str] = None
    content_type: str
    title: str
    content: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    comments_keywords: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    manual_note: Optional[str] = None


class ContentAssetUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    manual_note: Optional[str] = None


class ContentAssetResponse(BaseModel):
    id: int
    platform: str
    source_url: Optional[str]
    content_type: str
    title: str
    author: Optional[str]
    publish_time: Optional[datetime]
    tags: List[str]
    heat_score: float
    is_viral: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ===== AI Rewrite Schemas =====
class AIRewriteRequest(BaseModel):
    content_id: int
    target_platform: str  # xiaohongshu, douyin, zhihu, etc.
    content_type: str  # post, video, answer, etc.
    style: Optional[str] = "formal"
    marketing_strength: str = Field(default="medium")  # low, medium, high
    target_audience: Optional[str] = None
    topic_name: Optional[str] = None          # 关联洞察主题，自动拉取知识库参考
    audience_tags: List[str] = Field(default_factory=list)  # 目标人群标签


class AIRewriteResponse(BaseModel):
    id: int
    source_id: int
    target_platform: str
    rewritten_content: str
    risk_level: str
    compliance_score: float
    compliance_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ArkVisionRequest(BaseModel):
    image_url: str
    text: str = Field(default="你看见了什么？")
    model: Optional[str] = None


class ArkVisionResponse(BaseModel):
    model: str
    image_url: str
    text: str
    answer: str


# ===== Compliance Check Schemas =====
class ComplianceCheckRequest(BaseModel):
    content: str
    content_type: Optional[str] = "post"


class ComplianceCheckResponse(BaseModel):
    risk_level: str  # low, medium, high
    risk_score: float  # 0-100
    risk_points: List[Dict[str, str]]  # [{type, text, reason, suggestion}]
    suggestions: List[str]
    is_compliant: bool


# ===== Customer Schemas =====
class CustomerCreate(BaseModel):
    nickname: str
    wechat_id: Optional[str] = None
    phone: Optional[str] = None
    source_platform: str
    source_content_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    intention_level: str = "medium"
    inquiry_content: Optional[str] = None


class CustomerUpdate(BaseModel):
    nickname: Optional[str] = None
    wechat_id: Optional[str] = None
    tags: Optional[List[str]] = None
    intention_level: Optional[str] = None
    customer_status: Optional[str] = None


class CustomerFollowRecord(BaseModel):
    content: str
    follow_date: Optional[datetime] = None


class CustomerResponse(BaseModel):
    id: int
    nickname: str
    wechat_id: Optional[str]
    source_platform: str
    tags: List[str]
    intention_level: str
    customer_status: str
    follow_records: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Publish Record Schemas =====
class PublishRecordCreate(BaseModel):
    rewritten_content_id: int
    platform: str
    account_name: str
    published_by: Optional[str] = None


class PublishRecordUpdate(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    favorites: Optional[int] = None
    shares: Optional[int] = None
    private_messages: Optional[int] = None
    wechat_adds: Optional[int] = None
    leads: Optional[int] = None
    valid_leads: Optional[int] = None
    conversions: Optional[int] = None


class PublishRecordResponse(BaseModel):
    id: int
    platform: str
    account_name: str
    publish_time: datetime
    views: int
    likes: int
    comments: int
    private_messages: int
    wechat_adds: int
    valid_leads: int
    conversions: int

    class Config:
        from_attributes = True


# ===== Dashboard Schemas =====
class DashboardSummary(BaseModel):
    today_new_customers: int
    today_wechat_adds: int
    today_leads: int
    today_valid_leads: int
    today_conversions: int
    pending_follow_count: int
    pending_review_count: int


class DayTrendData(BaseModel):
    date: str
    publish_count: int
    total_views: int
    total_private_messages: int
    total_wechat_adds: int
    total_leads: int
    total_valid_leads: int
    total_conversions: int


class TrendResponse(BaseModel):
    data: List[DayTrendData]
    period: str = "7days"


class AICallStatItem(BaseModel):
    date: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    call_count: int
    failed_count: int
    failure_rate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    avg_latency_ms: float


class AICallStatsResponse(BaseModel):
    period_days: int
    scope: str
    data: List[AICallStatItem]


class PlatformAnalytics(BaseModel):
    platform: str
    publish_count: int
    total_leads: int
    total_valid_leads: int
    total_conversions: int


class TopicPerformance(BaseModel):
    topic: str
    publish_count: int
    total_views: int
    total_wechat_adds: int
    total_valid_leads: int
    wechat_add_rate: float
    valid_lead_rate: float
    conversion_rate: float


# ===== Browser Plugin Schemas =====
class PluginContentCreate(BaseModel):
    platform: str
    title: str
    content: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    comments_json: List[Dict[str, Any]] = Field(default_factory=list)
    url: str
    heat_score: Optional[float] = 0.0


class PluginContentResponse(BaseModel):
    id: int
    platform: str
    title: str
    author: Optional[str]
    url: str
    heat_score: float
    is_viral: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Collect (素材中台) Schemas =====

class CollectSaveRequest(BaseModel):
    """Save collected material – superset of ContentAssetCreate"""
    platform: str
    source_url: Optional[str] = None
    content_type: str = "post"
    title: str
    content: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    comments_keywords: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    manual_note: Optional[str] = None
    source_type: str = "paste"   # link | paste | import
    category: Optional[str] = None


class CollectUpdateRequest(BaseModel):
    tags: Optional[List[str]] = None
    manual_note: Optional[str] = None
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None


class ParseLinkRequest(BaseModel):
    url: str


class ParseLinkResponse(BaseModel):
    platform: str
    platform_label: str
    source_url: str
    detected_title: str
    detected_content: str
    detected_author: str
    fetch_success: bool
    message: str


class CollectAnalyzeResponse(BaseModel):
    content_id: int
    tags: List[str]
    category: str
    heat_score: float
    is_viral: bool
    viral_reasons: List[str]
    key_selling_points: List[str]
    rewrite_hints: str


class ContentAssetDetailResponse(BaseModel):
    """Full content asset with body and collect fields"""
    id: int
    platform: str
    source_url: Optional[str]
    content_type: str
    title: str
    content: str
    author: Optional[str]
    publish_time: Optional[datetime]
    tags: List[str]
    heat_score: float
    is_viral: bool
    source_type: Optional[str]
    category: Optional[str]
    manual_note: Optional[str]
    metrics: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 爆款内容采集分析中心 Schemas =====

class InsightTopicCreate(BaseModel):
    name: str = Field(..., max_length=64)
    description: Optional[str] = None
    platform_focus: List[str] = Field(default_factory=list)
    audience_tags: List[str] = Field(default_factory=list)
    risk_notes: Optional[str] = None


class InsightTopicResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    platform_focus: List[str]
    audience_tags: List[str]
    common_titles: List[str]
    common_pain_points: List[str]
    common_structures: List[str]
    common_ctas: List[str]
    risk_notes: Optional[str]
    content_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class InsightContentImport(BaseModel):
    """单条内容导入 – 手动录入 / 链接解析后提交 / 插件上传"""
    platform: str
    title: str
    body_text: str
    source_url: Optional[str] = None
    content_type: str = "post"
    author_name: Optional[str] = None
    author_profile_url: Optional[str] = None
    fans_count: Optional[int] = None
    account_positioning: Optional[str] = None  # 流量号/专业顾问号/案例号/清单号/避坑号
    publish_time: Optional[datetime] = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: int = 0
    view_count: int = 0
    topic_name: Optional[str] = None           # 直接关联到现有主题名
    audience_tags: List[str] = Field(default_factory=list)
    manual_note: Optional[str] = None
    source_type: str = "manual"                # manual / import / plugin
    raw_payload: Optional[Dict[str, Any]] = None


class InsightBatchImport(BaseModel):
    """批量导入 – JSON 数组"""
    items: List[InsightContentImport] = Field(..., min_length=1, max_length=200)


class InsightContentResponse(BaseModel):
    id: int
    platform: str
    source_url: Optional[str]
    content_type: str
    title: str
    body_text: str
    content_summary: Optional[str]
    author_name: Optional[str]
    publish_time: Optional[datetime]
    like_count: int
    comment_count: int
    share_count: int
    collect_count: int
    view_count: int
    engagement_score: float
    is_hot: bool
    heat_tier: str
    topic_id: Optional[int]
    audience_tags: List[str]
    structure_type: Optional[str]
    hook_type: Optional[str]
    tone_style: Optional[str]
    cta_type: Optional[str]
    emotion_level: int
    info_density: int
    title_formula: Optional[str]
    pain_points: List[str]
    highlights: List[str]
    ai_analyzed: bool
    risk_level: str
    risk_flags: List[str]
    manual_note: Optional[str]
    source_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class InsightAnalyzeResponse(BaseModel):
    content_id: int
    topic_name: Optional[str]
    audience_tags: List[str]
    structure_type: str
    hook_type: str
    tone_style: str
    cta_type: str
    emotion_level: int
    info_density: int
    title_formula: str
    pain_points: List[str]
    highlights: List[str]
    is_hot: bool
    heat_tier: str
    risk_level: str
    risk_flags: List[str]
    content_summary: str


class InsightAuthorResponse(BaseModel):
    id: int
    platform: str
    author_name: str
    author_profile_url: Optional[str]
    fans_count: Optional[int]
    account_type: Optional[str]
    account_tags: List[str]
    topic_coverage: Dict[str, Any]
    style_summary: Dict[str, Any]
    viral_rate: float
    avg_engagement: float
    primary_topic_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class InsightRetrieveRequest(BaseModel):
    """检索召回请求 – 给文案生成模块提供参考上下文"""
    platform: str
    topic_name: Optional[str] = None
    audience_tags: List[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class InsightRetrieveResponse(BaseModel):
    """检索召回结果 – 结构化参考特征，不返回原文"""
    topic_name: Optional[str]
    platform: str
    title_examples: List[str]
    structure_examples: List[str]
    hook_examples: List[str]
    cta_examples: List[str]
    pain_point_examples: List[str]
    style_summary: str
    risk_reminder: str
    reference_count: int
