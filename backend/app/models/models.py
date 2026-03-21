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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contents = relationship("ContentAsset", back_populates="owner")
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
    
    tags = Column(JSON, default=list)
    intention_level = Column(String(16), default="medium")  # low, medium, high
    customer_status = Column(String(32), default="new")
    
    inquiry_content = Column(Text, nullable=True)
    follow_records = Column(JSON, default=list)  # [{date, content, owner}, ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customers")


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
