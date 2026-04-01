"""
基础模型定义模块

包含：
- Base: SQLAlchemy declarative_base 实例
- TimestampMixin: 创建时间和更新时间混入类
- SoftDeleteMixin: 软删除混入类
"""

from datetime import datetime

# 从core.database导入Base，确保全局唯一
from app.core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class TimestampMixin:
    """时间戳混入类，自动管理 created_at 和 updated_at"""

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    """软删除混入类 - 为模型添加软删除支持

    使用方式：
        class MyModel(Base, SoftDeleteMixin):
            __tablename__ = "my_table"
            # ... 其他字段

    查询时过滤已删除记录：
        db.query(MyModel).filter(MyModel.is_deleted == False).all()
    """

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, nullable=True)  # 删除操作的用户ID

    def soft_delete(self, user_id: int = None):
        """标记为已删除

        Args:
            user_id: 执行删除操作的用户ID，用于审计
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id

    def restore(self):
        """恢复已删除记录"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None

    @classmethod
    def filter_not_deleted(cls, query):
        """查询过滤器 - 排除已删除记录

        使用示例：
            query = db.query(MyModel)
            query = MyModel.filter_not_deleted(query)
        """
        return query.filter(cls.is_deleted == False)


# 导出常用列类型，方便其他模块使用
__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin"]
