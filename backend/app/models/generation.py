"""
内容生成模块

包含：
- GenerationTask: 生成任务
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class GenerationTask(Base):
    """Persisted generation outputs and context snapshot."""

    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    material_item_id = Column(Integer, ForeignKey("material_items.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(50), nullable=False, index=True)
    account_type = Column(String(50), nullable=False, index=True)
    target_audience = Column(String(50), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, index=True)
    prompt_snapshot = Column(Text, nullable=True)
    output_text = Column(Text, nullable=False)
    reference_document_ids = Column(JSON, default=list)
    tags_json = Column(JSON, default=dict)
    copies_json = Column(JSON, default=list)
    compliance_json = Column(JSON, default=dict)
    selected_variant = Column(String(64), nullable=True)
    selected_variant_index = Column(Integer, nullable=True)
    adoption_status = Column(String(20), nullable=False, default="pending", index=True)
    adopted_at = Column(DateTime, nullable=True)
    adopted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    material_item = relationship("MaterialItem", back_populates="generation_tasks")


__all__ = ["GenerationTask"]
