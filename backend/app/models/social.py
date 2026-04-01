"""
社交账号与会话模块

包含：
- SocialAccount: 社交媒体账号
- Conversation: 会话记录
- Message: 消息记录
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class SocialAccount(Base):
    """Social media account binding for publish tasks"""

    __tablename__ = "social_accounts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(32), nullable=False)  # xiaohongshu/douyin/zhihu/weixin 等
    account_id = Column(String(200), nullable=True)  # 平台内账号ID
    account_name = Column(String(100), nullable=False)  # 显示名称
    avatar_url = Column(String(500), nullable=True)  # 头像
    status = Column(String(32), default="active")  # active/inactive/expired
    followers_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)  # 备注
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User")


class Conversation(Base):
    """会话记录"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    platform = Column(String(32), nullable=False)
    conversation_type = Column(String(32), nullable=False)  # comment / private_message
    external_id = Column(String(128), nullable=True)
    status = Column(String(32), default="active")  # active / closed / takeover
    ai_handled = Column(Boolean, default=True)
    takeover_at = Column(DateTime, nullable=True)
    takeover_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead", backref="conversations")
    customer = relationship("Customer", backref="conversations")
    takeover_user = relationship("User", backref="takeover_conversations")
    messages = relationship("Message", backref="conversation", lazy="dynamic")


class Message(Base):
    """消息记录"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(16), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    intent = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    reply_suggestion = Column(JSON, nullable=True)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = ["SocialAccount", "Conversation", "Message"]
