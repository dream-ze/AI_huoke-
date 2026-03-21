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
