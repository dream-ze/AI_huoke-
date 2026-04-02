from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


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
    role: str = "operator"
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserSummaryResponse(BaseModel):
    id: int
    username: str
    role: str = "operator"
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MobileH5TicketCreateRequest(BaseModel):
    redirect_path: Optional[str] = None
    api_base_url: Optional[str] = None


class MobileH5TicketResponse(BaseModel):
    ticket: str
    expires_in: int
    auth_url: Optional[str] = None


class WecomOAuthConfigResponse(BaseModel):
    """返回给前端的企业微信 OAuth 公开配置（不含 secret）"""

    corp_id: str
    agent_id: str
    oauth_enabled: bool


class WecomBindRequest(BaseModel):
    """管理员为当前登录用户绑定企业微信 userid"""

    wecom_userid: str = Field(min_length=1, max_length=64)


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
    topic_name: Optional[str] = None  # 关联洞察主题，自动拉取知识库参考
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
    # 扩展字段
    company: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    deal_value: Optional[float] = 0
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdate(BaseModel):
    nickname: Optional[str] = None
    wechat_id: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    intention_level: Optional[str] = None
    customer_status: Optional[str] = None
    # 扩展字段
    company: Optional[str] = None
    position: Optional[str] = None
    industry: Optional[str] = None
    deal_value: Optional[float] = None
    email: Optional[str] = None
    address: Optional[str] = None


class CustomerFollowRecord(BaseModel):
    content: str
    follow_date: Optional[datetime] = None


class CustomerResponse(BaseModel):
    id: int
    nickname: str
    wechat_id: Optional[str]
    phone: Optional[str]
    source_platform: str
    tags: List[str]
    intention_level: str
    customer_status: str
    follow_records: List[Dict[str, Any]]
    # 扩展字段
    company: Optional[str]
    position: Optional[str]
    industry: Optional[str]
    deal_value: Optional[float]
    email: Optional[str]
    address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    platform: str
    title: str
    source: str = "manual"
    post_url: Optional[str] = None
    wechat_adds: int = 0
    leads: int = 0
    valid_leads: int = 0
    conversions: int = 0
    status: str = "new"
    intention_level: str = "medium"
    note: Optional[str] = None


class LeadFromPublishRequest(BaseModel):
    """从发布内容创建线索的请求"""

    published_content_id: int = Field(..., description="发布内容ID")
    platform: str = Field(..., description="触点平台")
    contact_info: Dict[str, Optional[str]] = Field(
        default_factory=dict, description="联系信息，包含 phone(手机)/wechat(微信)"
    )
    channel: str = Field(..., description="渠道: 私信/表单/加微")
    audience_tags: List[str] = Field(default_factory=list, description="受众标签")
    notes: Optional[str] = Field(None, description="备注")


class LeadBatchImportRequest(BaseModel):
    """批量导入线索请求"""

    leads: List[LeadCreate] = Field(..., min_length=1, max_length=500, description="线索数据列表")


class LeadBatchImportResponse(BaseModel):
    """批量导入线索响应"""

    total: int = Field(..., description="总数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    duplicates: int = Field(default=0, description="重复数")
    created_ids: List[int] = Field(default_factory=list, description="创建的线索ID列表")
    failed_details: List[Dict[str, Any]] = Field(default_factory=list, description="失败详情")


class LeadStatusUpdate(BaseModel):
    status: str


class LeadAssignRequest(BaseModel):
    owner_id: Optional[int] = None


class LeadConvertCustomerRequest(BaseModel):
    nickname: Optional[str] = None
    wechat_id: Optional[str] = None
    phone: Optional[str] = None
    intention_level: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    inquiry_content: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    owner_id: int
    publish_task_id: Optional[int]
    platform: str
    source: str
    title: str
    post_url: Optional[str]
    wechat_adds: int
    leads: int
    valid_leads: int
    conversions: int
    status: str
    intention_level: str
    note: Optional[str]
    customer_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadTraceResponse(LeadResponse):
    customer_id: Optional[int] = None
    publish_record_id: Optional[int] = None


class InsightAnalyzeBatchTaskResponse(BaseModel):
    id: int
    platform: str
    collect_mode: str
    target_value: Optional[str]
    status: str
    result_count: int
    notes: Optional[str]
    created_at: datetime
    run_at: Optional[datetime]

    class Config:
        from_attributes = True


class SystemVersionResponse(BaseModel):
    api_version: str
    app_name: str
    release_channel: str
    min_desktop_version: Optional[str] = None
    latest_desktop_version: Optional[str] = None


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


class PublishTaskCreate(BaseModel):
    rewritten_content_id: Optional[int] = None
    platform: str
    account_name: str
    task_title: str
    content_text: str
    assigned_to: Optional[int] = None
    due_time: Optional[datetime] = None


class PublishTaskSubmit(BaseModel):
    post_url: Optional[str] = None
    posted_at: Optional[datetime] = None
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
    note: Optional[str] = None


class PublishTaskActionRequest(BaseModel):
    note: Optional[str] = None


class PublishTaskAssignRequest(BaseModel):
    assigned_to: int = Field(..., ge=1)
    note: Optional[str] = None


class PublishTaskFeedbackResponse(BaseModel):
    id: int
    action: str
    note: Optional[str]
    payload: Dict[str, Any]
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class PublishTaskResponse(BaseModel):
    id: int
    owner_id: int
    rewritten_content_id: Optional[int]
    publish_record_id: Optional[int]
    platform: str
    account_name: str
    task_title: str
    content_text: str
    status: str
    assigned_to: Optional[int]
    due_time: Optional[datetime]
    claimed_at: Optional[datetime]
    posted_at: Optional[datetime]
    closed_at: Optional[datetime]
    post_url: Optional[str]
    reject_reason: Optional[str]
    close_reason: Optional[str]
    views: int
    likes: int
    comments: int
    favorites: int
    shares: int
    private_messages: int
    wechat_adds: int
    leads: int
    valid_leads: int
    conversions: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublishTaskDetailResponse(PublishTaskResponse):
    feedbacks: List[PublishTaskFeedbackResponse] = Field(default_factory=list)


class PublishTaskStatsResponse(BaseModel):
    total: int
    pending: int
    claimed: int
    submitted: int
    rejected: int
    closed: int


# ===== Publish Stats Schemas =====
class PlatformStatsResponse(BaseModel):
    """Platform performance comparison stats."""

    platform: str
    total_tasks: int
    completed_tasks: int
    total_views: int
    total_likes: int
    total_comments: int
    total_wechat_adds: int
    total_leads: int
    total_valid_leads: int
    total_conversions: int
    avg_views_per_task: float
    conversion_rate: float


class RoiTrendItem(BaseModel):
    """Daily ROI trend data."""

    date: str
    publish_count: int
    total_leads: int
    total_valid_leads: int
    total_conversions: int
    lead_rate: float
    conversion_rate: float


class ContentAnalysisItem(BaseModel):
    """Content type performance analysis."""

    platform: str
    task_count: int
    avg_views: float
    avg_likes: float
    avg_wechat_adds: float
    avg_conversions: float
    best_task_title: Optional[str] = None
    best_task_conversions: int = 0


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
    synced_content_asset_id: Optional[int] = None
    synced_insight_item_id: Optional[int] = None
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
    source_type: str = "paste"  # link | paste | import
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


class CollectIntakeRequest(BaseModel):
    """Unified intake for multi-channel acquisition into inbox."""

    platform: str
    source_url: Optional[str] = None
    content_type: str = "post"
    title: str
    content: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    manual_note: Optional[str] = None
    source_type: Literal[
        "link",
        "paste",
        "import",
        "plugin",
        "mobile_share",
        "screenshot_ocr",
        "wechat_forward",
    ] = "paste"
    category: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    client_request_id: Optional[str] = Field(default=None, min_length=8, max_length=128)


class CollectIntakeResponse(BaseModel):
    inbox_id: int
    status: str
    source_type: str
    dedupe_hit: bool = False
    duplicate_ids: List[int] = Field(default_factory=list)
    message: str


class CollectOcrResponse(BaseModel):
    extracted_text: str
    engine: str
    warnings: List[str] = Field(default_factory=list)
    inbox_id: Optional[int] = None
    dedupe_hit: bool = False
    message: str


class InboxCreateRequest(BaseModel):
    platform: str
    source_url: Optional[str] = None
    content_type: str = "post"
    title: str
    content: str
    author: Optional[str] = None
    publish_time: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    manual_note: Optional[str] = None
    source_type: str = "paste"
    category: Optional[str] = None


class InboxUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    manual_note: Optional[str] = None
    review_note: Optional[str] = None
    assignee_user_id: Optional[int] = None


class InboxResponse(BaseModel):
    id: int
    platform: str
    source_url: Optional[str]
    content_type: str
    title: str
    content: str
    author: Optional[str]
    publish_time: Optional[datetime]
    tags: List[str]
    metrics: Dict[str, Any]
    source_type: Optional[str]
    category: Optional[str]
    manual_note: Optional[str]
    heat_score: float
    is_viral: bool
    status: str
    assigned_to: Optional[int]
    assigned_at: Optional[datetime]
    promoted_content_id: Optional[int]
    promoted_insight_item_id: Optional[int]
    review_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class InboxPromoteResponse(BaseModel):
    inbox_id: int
    status: str
    content_asset_id: int
    insight_item_id: int


class InboxStatsResponse(BaseModel):
    total: int
    pending: int
    analyzed: int
    imported: int
    discarded: int
    by_platform: Dict[str, int]


class InboxBatchAssignRequest(BaseModel):
    inbox_ids: List[int] = Field(min_length=1, max_length=200)
    assignee_user_id: int = Field(..., ge=1)
    note_template: Optional[str] = None


class InboxBatchDiscardRequest(BaseModel):
    inbox_ids: List[int] = Field(min_length=1, max_length=200)
    review_note: str = Field(..., min_length=4, max_length=500)


class InboxBatchPromoteRequest(BaseModel):
    inbox_ids: List[int] = Field(min_length=1, max_length=200)


class InboxAutoMergeRequest(BaseModel):
    keep_strategy: Literal["latest", "earliest"] = "latest"
    dry_run: bool = True


class InboxBatchActionResponse(BaseModel):
    total: int
    success: int
    failed: int
    details: List[Dict[str, Any]] = Field(default_factory=list)


class InboxDedupeGroup(BaseModel):
    key: str
    count: int
    inbox_ids: List[int] = Field(default_factory=list)
    titles: List[str] = Field(default_factory=list)


class InboxDedupePreviewResponse(BaseModel):
    duplicate_groups: List[InboxDedupeGroup] = Field(default_factory=list)
    total_duplicates: int


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
    topic_name: Optional[str] = None  # 直接关联到现有主题名
    audience_tags: List[str] = Field(default_factory=list)
    manual_note: Optional[str] = None
    source_type: str = "manual"  # manual / import / plugin
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


# ===== 文案改写 Schemas =====
Platform = Literal["xiaohongshu", "douyin", "zhihu"]
AccountType = Literal["personal_ip", "sales", "agency"]
ToneType = Literal["natural", "emotional", "professional"]


class MaterialTagRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content_text: str = Field(..., min_length=1)
    platform: Platform = "xiaohongshu"
    keyword: Optional[str] = None
    author_name: Optional[str] = None
    publish_time: Optional[str] = None


class TagResult(BaseModel):
    topic_tag: str
    intent_tag: str
    crowd_tag: str
    risk_tag: str
    heat_score: int
    reason: str


class TagResponse(BaseModel):
    success: bool = True
    data: TagResult


class CopyGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content_text: str = Field(..., min_length=1)
    platform: Platform = "xiaohongshu"
    account_type: AccountType = "sales"
    target_audience: str = "负债人群"
    tone: ToneType = "natural"

    topic_tag: Optional[str] = None
    intent_tag: Optional[str] = None
    crowd_tag: Optional[str] = None
    keyword: Optional[str] = None


class CopyVariant(BaseModel):
    variant_name: str
    title: str
    content: str
    hashtags: List[str]


class CopyGenerateResponse(BaseModel):
    success: bool = True
    tags: TagResult
    copies: List[CopyVariant]


# ===== Social Account Schemas =====
class SocialAccountCreate(BaseModel):
    platform: str
    account_name: str
    account_id: Optional[str] = None
    avatar_url: Optional[str] = None
    notes: Optional[str] = None


class SocialAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    followers_count: Optional[int] = None
    notes: Optional[str] = None


class SocialAccountResponse(BaseModel):
    id: int
    owner_id: int
    platform: str
    account_id: Optional[str]
    account_name: str
    avatar_url: Optional[str]
    status: str
    followers_count: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SocialAccountPlatform(BaseModel):
    value: str
    label: str


# ===== Platform Rule Management Schemas =====
class PlatformRuleCreate(BaseModel):
    """创建平台合规规则请求"""

    platform: str = Field(..., description="平台名称 (xiaohongshu/douyin/zhihu)")
    keyword_or_pattern: str = Field(..., min_length=1, max_length=500, description="关键词或正则表达式")
    risk_level: str = Field(..., description="风险等级 (high/medium/low)")
    suggestion: str = Field(..., description="修改建议")
    rule_category: str = Field(..., description="规则分类")
    description: Optional[str] = Field(None, description="规则描述")


class PlatformRuleUpdate(BaseModel):
    """更新平台合规规则请求"""

    keyword_or_pattern: Optional[str] = Field(None, min_length=1, max_length=500)
    risk_level: Optional[str] = Field(None, description="风险等级 (high/medium/low)")
    suggestion: Optional[str] = Field(None)
    rule_category: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None, description="是否激活")


class PlatformRuleResponse(BaseModel):
    """平台合规规则响应"""

    id: int
    platform: str
    keyword_or_pattern: str
    risk_level: str
    suggestion: str
    rule_category: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlatformRuleListResponse(BaseModel):
    """平台规则列表响应"""

    items: List[PlatformRuleResponse]
    total: int
    page: int
    size: int


class PlatformRuleImportResponse(BaseModel):
    """YAML导入规则响应"""

    platform: str
    imported_count: int
    skipped_count: int
    total_count: int
    message: str


class PlatformRuleReloadCacheResponse(BaseModel):
    """刷新规则缓存响应"""

    success: bool
    platforms: List[str]
    message: str


# ===== Attribution Schemas =====
class AttributionCreate(BaseModel):
    """归因创建请求"""

    platform: str = Field(..., description="触点平台")
    account_id: Optional[int] = Field(None, description="发布账号ID")
    content_id: Optional[int] = Field(None, description="发布内容ID")
    campaign_id: Optional[int] = Field(None, description="活动ID")
    audience_tags: List[str] = Field(default_factory=list, description="受众标签")
    topic_tags: List[str] = Field(default_factory=list, description="主题标签")
    channel: Optional[str] = Field(None, description="渠道")
    first_contact_time: Optional[datetime] = Field(None, description="首次接触时间")
    touchpoint_url: Optional[str] = Field(None, description="触点URL")
    attribution_type: str = Field(default="last_touch", description="归因类型")


class AttributionChainResponse(BaseModel):
    """完整归因链响应"""

    lead_id: int
    platform: Optional[str] = None
    account_name: Optional[str] = None
    content_title: Optional[str] = None
    campaign_name: Optional[str] = None
    audience_tags: List[str] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)
    channel: Optional[str] = None
    first_contact_time: Optional[datetime] = None
    current_stage: str = "new"
    conversion_result: Optional[str] = None
    touchpoint_url: Optional[str] = None


class ContentROIResponse(BaseModel):
    """内容ROI响应"""

    content_id: int
    content_title: Optional[str] = None
    platform: Optional[str] = None
    lead_count: int = 0
    conversion_count: int = 0
    stage_distribution: Dict[str, int] = Field(default_factory=dict)
    conversion_rate: float = 0.0


class CampaignAttributionReport(BaseModel):
    """活动归因报告响应"""

    campaign_id: int
    campaign_name: Optional[str] = None
    total_leads: int = 0
    total_conversions: int = 0
    by_platform: List[Dict[str, Any]] = Field(default_factory=list)
    by_account: List[Dict[str, Any]] = Field(default_factory=list)
    by_content: List[Dict[str, Any]] = Field(default_factory=list)
    date_range: Dict[str, Optional[str]] = Field(default_factory=dict)


class PlatformAttributionSummary(BaseModel):
    """平台归因汇总"""

    platform: str
    lead_count: int = 0
    conversion_count: int = 0
    conversion_rate: float = 0.0
    valid_lead_count: int = 0


class AccountAttributionSummary(BaseModel):
    """账号归因汇总"""

    account_id: Optional[int] = None
    account_name: str
    platform: Optional[str] = None
    lead_count: int = 0
    conversion_count: int = 0
    conversion_rate: float = 0.0
    valid_lead_count: int = 0


# ===== Three Layer Dashboard Schemas =====
class ContentLayerMetrics(BaseModel):
    """内容层指标"""

    today_generation_count: int = Field(default=0, description="今日生成数")
    compliance_pass_rate: float = Field(default=0.0, description="合规通过率(%)")
    adoption_rate: float = Field(default=0.0, description="人工采纳率(%)")
    publish_rate: float = Field(default=0.0, description="发布率(%)")
    total_materials: int = Field(default=0, description="素材总数")
    knowledge_items: int = Field(default=0, description="知识库条目数")


class AcquisitionLayerMetrics(BaseModel):
    """获客层指标"""

    total_leads: int = Field(default=0, description="总线索数")
    leads_by_platform: List[Dict[str, Any]] = Field(
        default_factory=list, description="各平台线索数 [{platform, count}]"
    )
    leads_by_account: List[Dict[str, Any]] = Field(
        default_factory=list, description="各账号线索数 [{account_name, count}]"
    )
    leads_by_topic: List[Dict[str, Any]] = Field(default_factory=list, description="各主题线索数 [{topic, count}]")
    wechat_add_rate: float = Field(default=0.0, description="加微率(%)")
    contact_rate: float = Field(default=0.0, description="留资率(%)")


class ConversionLayerMetrics(BaseModel):
    """转化层指标"""

    grade_distribution: Dict[str, float] = Field(
        default_factory=dict, description="ABCD线索占比 {A: %, B: %, C: %, D: %}"
    )
    avg_first_response_hours: float = Field(default=0.0, description="平均首次响应时长(小时)")
    followup_completion_rate: float = Field(default=0.0, description="跟进完成率(%)")
    conversion_rate: float = Field(default=0.0, description="成交/放款转化率(%)")
    total_converted: int = Field(default=0, description="总转化数")
    total_revenue: float = Field(default=0.0, description="预估收入")


class ThreeLayerDashboard(BaseModel):
    """三层看板总览"""

    content: ContentLayerMetrics
    acquisition: AcquisitionLayerMetrics
    conversion: ConversionLayerMetrics
    period: str = Field(default="today", description="统计周期: today/week/month/all")
