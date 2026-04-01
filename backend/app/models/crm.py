"""
CRM客户关系管理模块

包含：
- Lead: 线索池实体
- Customer: 客户信息
- LeadProfile: 线索画像
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


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

    # 扩展字段
    company = Column(String(200), nullable=True)  # 公司名称
    position = Column(String(100), nullable=True)  # 职位
    industry = Column(String(100), nullable=True)  # 行业
    deal_value = Column(Float, nullable=True, default=0)  # 成交金额
    email = Column(String(200), nullable=True)  # 邮箱
    address = Column(String(500), nullable=True)  # 地址

    # 跟进时间字段
    next_follow_at = Column(DateTime, nullable=True)
    last_follow_at = Column(DateTime, nullable=True)
    last_reminder_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="customers")
    lead = relationship("Lead", back_populates="customer")


class LeadProfile(Base):
    """线索画像（自动抽取）"""

    __tablename__ = "lead_profiles"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)
    loan_amount_need = Column(String(32), nullable=True)
    has_house = Column(Boolean, nullable=True)
    has_car = Column(Boolean, nullable=True)
    has_provident_fund = Column(Boolean, nullable=True)
    credit_status = Column(String(32), nullable=True)  # good / fair / poor / unknown
    urgency_level = Column(String(16), nullable=True)  # high / medium / low
    extracted_phone = Column(String(20), nullable=True)
    extracted_wechat = Column(String(64), nullable=True)
    confidence_score = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead", backref="profile", uselist=False)


__all__ = ["Lead", "Customer", "LeadProfile"]
