"""
用户模型模块

包含：
- User: 用户模型
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship


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


__all__ = ["User"]
