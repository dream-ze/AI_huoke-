"""add knowledge chunks table and library fields

Revision ID: 20260329_02
Revises: enhance_knowledge_01
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa

revision = '20260329_02'
down_revision = 'enhance_knowledge_01'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 注意：pgvector 扩展需要超级用户权限，如需启用请手动执行:
    # CREATE EXTENSION IF NOT EXISTS vector;
    
    # 为 mvp_knowledge_items 添加新字段
    op.add_column('mvp_knowledge_items', sa.Column('library_type', sa.String(50), server_default='industry_phrases'))
    op.add_column('mvp_knowledge_items', sa.Column('layer', sa.String(30), server_default='structured'))
    op.add_column('mvp_knowledge_items', sa.Column('source_url', sa.String(500), nullable=True))
    op.add_column('mvp_knowledge_items', sa.Column('author', sa.String(200), nullable=True))
    op.add_column('mvp_knowledge_items', sa.Column('like_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_knowledge_items', sa.Column('comment_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_knowledge_items', sa.Column('collect_count', sa.Integer(), server_default='0'))
    op.add_column('mvp_knowledge_items', sa.Column('emotion_intensity', sa.String(20), nullable=True))
    op.add_column('mvp_knowledge_items', sa.Column('conversion_goal', sa.String(50), nullable=True))
    op.add_column('mvp_knowledge_items', sa.Column('is_hot', sa.Boolean(), server_default='false'))
    
    # 创建索引
    op.create_index('ix_mvp_knowledge_items_library_type', 'mvp_knowledge_items', ['library_type'])
    op.create_index('ix_mvp_knowledge_items_layer', 'mvp_knowledge_items', ['layer'])
    op.create_index('ix_mvp_knowledge_items_is_hot', 'mvp_knowledge_items', ['is_hot'])
    
    # 创建 mvp_knowledge_chunks 表
    op.create_table(
        'mvp_knowledge_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('knowledge_id', sa.Integer(), sa.ForeignKey('mvp_knowledge_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_type', sa.String(30), nullable=False),
        sa.Column('chunk_index', sa.Integer(), server_default='0'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('embedding', sa.Text(), nullable=True),
        sa.Column('token_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # 创建索引
    op.create_index('ix_mvp_knowledge_chunks_knowledge_id', 'mvp_knowledge_chunks', ['knowledge_id'])
    op.create_index('ix_mvp_knowledge_chunks_chunk_type', 'mvp_knowledge_chunks', ['chunk_type'])
    op.create_index('ix_mvp_knowledge_chunks_created_at', 'mvp_knowledge_chunks', ['created_at'])

def downgrade() -> None:
    op.drop_table('mvp_knowledge_chunks')
    op.drop_index('ix_mvp_knowledge_items_is_hot', 'mvp_knowledge_items')
    op.drop_index('ix_mvp_knowledge_items_layer', 'mvp_knowledge_items')
    op.drop_index('ix_mvp_knowledge_items_library_type', 'mvp_knowledge_items')
    op.drop_column('mvp_knowledge_items', 'is_hot')
    op.drop_column('mvp_knowledge_items', 'conversion_goal')
    op.drop_column('mvp_knowledge_items', 'emotion_intensity')
    op.drop_column('mvp_knowledge_items', 'collect_count')
    op.drop_column('mvp_knowledge_items', 'comment_count')
    op.drop_column('mvp_knowledge_items', 'like_count')
    op.drop_column('mvp_knowledge_items', 'author')
    op.drop_column('mvp_knowledge_items', 'source_url')
    op.drop_column('mvp_knowledge_items', 'layer')
    op.drop_column('mvp_knowledge_items', 'library_type')
