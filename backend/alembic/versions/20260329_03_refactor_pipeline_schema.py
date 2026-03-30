"""refactor pipeline schema for four-layer link

Revision ID: 20260329_03
Revises: 20260329_02
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa


revision = '20260329_03'
down_revision = '20260329_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────
    # 1. MvpInboxItem 新增字段
    # ─────────────────────────────────────────────────────────────
    op.add_column('mvp_inbox_items', sa.Column('source_id', sa.String(200), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('content_preview', sa.Text(), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('author_name', sa.String(200), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('publish_time', sa.DateTime(), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('url', sa.String(500), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('like_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_inbox_items', sa.Column('comment_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_inbox_items', sa.Column('favorite_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_inbox_items', sa.Column('clean_status', sa.String(20), server_default='pending'))
    op.add_column('mvp_inbox_items', sa.Column('quality_status', sa.String(20), server_default='pending'))
    op.add_column('mvp_inbox_items', sa.Column('risk_status', sa.String(20), server_default='normal'))
    op.add_column('mvp_inbox_items', sa.Column('quality_score', sa.Float(), server_default='0.0'))
    op.add_column('mvp_inbox_items', sa.Column('risk_score', sa.Float(), server_default='0.0'))
    op.add_column('mvp_inbox_items', sa.Column('material_status', sa.String(20), server_default='not_in'))
    op.add_column('mvp_inbox_items', sa.Column('cleaned_at', sa.DateTime(), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('screened_at', sa.DateTime(), nullable=True))
    op.add_column('mvp_inbox_items', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # 创建索引
    op.create_index('ix_mvp_inbox_items_source_id', 'mvp_inbox_items', ['source_id'])
    op.create_index('ix_mvp_inbox_items_clean_status', 'mvp_inbox_items', ['clean_status'])
    op.create_index('ix_mvp_inbox_items_quality_status', 'mvp_inbox_items', ['quality_status'])
    op.create_index('ix_mvp_inbox_items_risk_status', 'mvp_inbox_items', ['risk_status'])
    op.create_index('ix_mvp_inbox_items_material_status', 'mvp_inbox_items', ['material_status'])
    
    # ─────────────────────────────────────────────────────────────
    # 2. MvpMaterialItem 新增字段
    # ─────────────────────────────────────────────────────────────
    op.add_column('mvp_material_items', sa.Column('inbox_item_id', sa.Integer(), sa.ForeignKey('mvp_inbox_items.id'), nullable=True))
    op.add_column('mvp_material_items', sa.Column('quality_score', sa.Float(), nullable=True))
    op.add_column('mvp_material_items', sa.Column('risk_score', sa.Float(), nullable=True))
    op.add_column('mvp_material_items', sa.Column('tags_json', sa.Text(), nullable=True))
    op.add_column('mvp_material_items', sa.Column('topic', sa.String(100), nullable=True))
    op.add_column('mvp_material_items', sa.Column('persona', sa.String(100), nullable=True))
    op.add_column('mvp_material_items', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # 创建索引
    op.create_index('ix_mvp_material_items_inbox_item_id', 'mvp_material_items', ['inbox_item_id'])
    op.create_index('ix_mvp_material_items_topic', 'mvp_material_items', ['topic'])
    op.create_index('ix_mvp_material_items_persona', 'mvp_material_items', ['persona'])
    
    # ─────────────────────────────────────────────────────────────
    # 3. MvpKnowledgeChunk embedding 字段
    # ─────────────────────────────────────────────────────────────
    # 使用 Text 类型存储 embedding（pgvector 未安装时）
    op.drop_column('mvp_knowledge_chunks', 'embedding')
    op.add_column('mvp_knowledge_chunks', sa.Column('embedding', sa.Text(), nullable=True))
    
    # ─────────────────────────────────────────────────────────────
    # 4. MvpKnowledgeItem embedding 字段
    # ─────────────────────────────────────────────────────────────
    # 使用 Text 类型存储 embedding（pgvector 未安装时）
    op.drop_column('mvp_knowledge_items', 'embedding')
    op.add_column('mvp_knowledge_items', sa.Column('embedding', sa.Text(), nullable=True))


def downgrade() -> None:
    # ─────────────────────────────────────────────────────────────
    # 4. MvpKnowledgeItem 回滚 embedding 字段
    # ─────────────────────────────────────────────────────────────
    op.drop_index('ix_mvp_knowledge_items_embedding', 'mvp_knowledge_items')
    op.drop_column('mvp_knowledge_items', 'embedding')
    op.add_column('mvp_knowledge_items', sa.Column('embedding', sa.Text(), nullable=True))
    
    # ─────────────────────────────────────────────────────────────
    # 3. MvpKnowledgeChunk 回滚 embedding 字段
    # ─────────────────────────────────────────────────────────────
    op.drop_index('ix_mvp_knowledge_chunks_embedding', 'mvp_knowledge_chunks')
    op.drop_column('mvp_knowledge_chunks', 'embedding')
    op.add_column('mvp_knowledge_chunks', sa.Column('embedding', sa.Text(), nullable=True))
    
    # ─────────────────────────────────────────────────────────────
    # 2. MvpMaterialItem 回滚新增字段
    # ─────────────────────────────────────────────────────────────
    op.drop_index('ix_mvp_material_items_persona', 'mvp_material_items')
    op.drop_index('ix_mvp_material_items_topic', 'mvp_material_items')
    op.drop_index('ix_mvp_material_items_inbox_item_id', 'mvp_material_items')
    op.drop_column('mvp_material_items', 'updated_at')
    op.drop_column('mvp_material_items', 'persona')
    op.drop_column('mvp_material_items', 'topic')
    op.drop_column('mvp_material_items', 'tags_json')
    op.drop_column('mvp_material_items', 'risk_score')
    op.drop_column('mvp_material_items', 'quality_score')
    op.drop_column('mvp_material_items', 'inbox_item_id')
    
    # ─────────────────────────────────────────────────────────────
    # 1. MvpInboxItem 回滚新增字段
    # ─────────────────────────────────────────────────────────────
    op.drop_index('ix_mvp_inbox_items_material_status', 'mvp_inbox_items')
    op.drop_index('ix_mvp_inbox_items_risk_status', 'mvp_inbox_items')
    op.drop_index('ix_mvp_inbox_items_quality_status', 'mvp_inbox_items')
    op.drop_index('ix_mvp_inbox_items_clean_status', 'mvp_inbox_items')
    op.drop_index('ix_mvp_inbox_items_source_id', 'mvp_inbox_items')
    op.drop_column('mvp_inbox_items', 'updated_at')
    op.drop_column('mvp_inbox_items', 'screened_at')
    op.drop_column('mvp_inbox_items', 'cleaned_at')
    op.drop_column('mvp_inbox_items', 'material_status')
    op.drop_column('mvp_inbox_items', 'risk_score')
    op.drop_column('mvp_inbox_items', 'quality_score')
    op.drop_column('mvp_inbox_items', 'risk_status')
    op.drop_column('mvp_inbox_items', 'quality_status')
    op.drop_column('mvp_inbox_items', 'clean_status')
    op.drop_column('mvp_inbox_items', 'favorite_count')
    op.drop_column('mvp_inbox_items', 'comment_count')
    op.drop_column('mvp_inbox_items', 'like_count')
    op.drop_column('mvp_inbox_items', 'url')
    op.drop_column('mvp_inbox_items', 'publish_time')
    op.drop_column('mvp_inbox_items', 'author_name')
    op.drop_column('mvp_inbox_items', 'content_preview')
    op.drop_column('mvp_inbox_items', 'source_id')
