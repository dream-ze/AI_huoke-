"""enhance knowledge schema with structured fields

Revision ID: enhance_knowledge_01
Revises: mvp_core_001
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa


revision = "enhance_knowledge_01"
down_revision = "mvp_core_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('mvp_knowledge_items', sa.Column('topic', sa.String(100), nullable=True, comment="内容主题：loan/credit/online_loan/housing_fund"))
    op.add_column('mvp_knowledge_items', sa.Column('content_type', sa.String(50), nullable=True, comment="内容类型：案例/知识/规则/模板"))
    op.add_column('mvp_knowledge_items', sa.Column('opening_type', sa.String(50), nullable=True, comment="开头方式：提问/数据/故事/痛点"))
    op.add_column('mvp_knowledge_items', sa.Column('hook_sentence', sa.Text(), nullable=True, comment="爆点句/钩子句"))
    op.add_column('mvp_knowledge_items', sa.Column('cta_style', sa.String(100), nullable=True, comment="转化方式：私信/评论/关注"))
    op.add_column('mvp_knowledge_items', sa.Column('risk_level', sa.String(20), nullable=True, comment="风险等级：low/medium/high"))
    op.add_column('mvp_knowledge_items', sa.Column('summary', sa.Text(), nullable=True, comment="内容摘要"))


def downgrade() -> None:
    op.drop_column('mvp_knowledge_items', 'summary')
    op.drop_column('mvp_knowledge_items', 'risk_level')
    op.drop_column('mvp_knowledge_items', 'cta_style')
    op.drop_column('mvp_knowledge_items', 'hook_sentence')
    op.drop_column('mvp_knowledge_items', 'opening_type')
    op.drop_column('mvp_knowledge_items', 'content_type')
    op.drop_column('mvp_knowledge_items', 'topic')
