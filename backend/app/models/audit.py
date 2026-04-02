"""
审计日志模型

用于持久化记录用户操作行为，支持审计追溯。
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, comment="操作用户ID")
    action = Column(String(50), nullable=False, comment="操作类型：create/update/delete/export/approve/assign")
    resource = Column(String(100), nullable=False, comment="资源类型：material/knowledge/customer/content")
    resource_id = Column(String(100), nullable=True, comment="资源ID")
    old_value = Column(Text, nullable=True, comment="变更前的值（JSON格式）")
    new_value = Column(Text, nullable=True, comment="变更后的值（JSON格式）")
    detail = Column(Text, nullable=True, comment="详细信息")
    result = Column(String(20), default="success", comment="操作结果：success/failure")
    ip_address = Column(String(50), nullable=True, comment="操作IP地址")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, resource={self.resource})>"


__all__ = ["AuditLog"]
