"""
知识库管理模块

包含：
- KnowledgeDocument: 知识文档
- KnowledgeChunk: 知识切块
- Rule: 生成规则
- PromptTemplate: 提示词模板
"""

from datetime import datetime

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class KnowledgeDocument(Base):
    """Structured knowledge extracted from materials."""

    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    material_item_id = Column(Integer, ForeignKey("material_items.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(50), nullable=False, index=True)
    account_type = Column(String(50), nullable=False, index=True)
    target_audience = Column(String(50), nullable=False, index=True)
    content_type = Column(String(50), nullable=False, index=True)
    topic = Column(Text, nullable=True)

    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    material_item = relationship("MaterialItem", back_populates="knowledge_documents")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="knowledge_document", cascade="all,delete-orphan")


class KnowledgeChunk(Base):
    """Retrieval chunks for knowledge documents."""

    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    knowledge_document_id = Column(
        Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chunk_type = Column(String(30), nullable=False, default="body")
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    keywords = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_document = relationship("KnowledgeDocument", back_populates="knowledge_chunks")


class Rule(Base):
    """Generation boundary constraints."""

    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    rule_type = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=True, index=True)
    account_type = Column(String(50), nullable=True, index=True)
    target_audience = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class PromptTemplate(Base):
    """Task-specific prompt templates."""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    task_type = Column(String(50), nullable=False, index=True)
    platform = Column(String(50), nullable=True, index=True)
    account_type = Column(String(50), nullable=True, index=True)
    target_audience = Column(String(50), nullable=True, index=True)
    version = Column(String(30), nullable=False, default="v1")
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


__all__ = ["KnowledgeDocument", "KnowledgeChunk", "Rule", "PromptTemplate"]
