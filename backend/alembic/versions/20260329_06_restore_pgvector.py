"""恢复 pgvector embedding 列

Revision ID: 20260329_06
Revises: 20260329_05
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260329_06'
down_revision = '20260329_05'
branch_labels = None
depends_on = None


def upgrade():
    # 确保 pgvector 扩展已创建
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # 删除 mvp_knowledge_items 表的 Text embedding 列（如果存在）
    op.execute("""
        ALTER TABLE mvp_knowledge_items 
        DROP COLUMN IF EXISTS embedding
    """)
    
    # 删除 mvp_knowledge_chunks 表的 Text embedding 列（如果存在）
    op.execute("""
        ALTER TABLE mvp_knowledge_chunks 
        DROP COLUMN IF EXISTS embedding
    """)
    
    # 添加 vector(768) 类型的 embedding 列到 mvp_knowledge_items
    op.execute("""
        ALTER TABLE mvp_knowledge_items 
        ADD COLUMN embedding vector(768)
    """)
    
    # 添加 vector(768) 类型的 embedding 列到 mvp_knowledge_chunks
    op.execute("""
        ALTER TABLE mvp_knowledge_chunks 
        ADD COLUMN embedding vector(768)
    """)
    
    # 创建向量索引（使用 ivfflat 或 hnsw，这里使用 ivfflat 作为通用选择）
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mvp_knowledge_items_embedding 
        ON mvp_knowledge_items 
        USING ivfflat (embedding vector_cosine_ops)
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mvp_knowledge_chunks_embedding 
        ON mvp_knowledge_chunks 
        USING ivfflat (embedding vector_cosine_ops)
    """)


def downgrade():
    # 删除索引
    op.execute("""
        DROP INDEX IF EXISTS ix_mvp_knowledge_chunks_embedding
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS ix_mvp_knowledge_items_embedding
    """)
    
    # 删除 vector 类型的 embedding 列
    op.execute("""
        ALTER TABLE mvp_knowledge_chunks 
        DROP COLUMN IF EXISTS embedding
    """)
    
    op.execute("""
        ALTER TABLE mvp_knowledge_items 
        DROP COLUMN IF EXISTS embedding
    """)
    
    # 添加回 Text 类型的 embedding 列
    op.add_column('mvp_knowledge_items', sa.Column('embedding', sa.Text(), nullable=True))
    op.add_column('mvp_knowledge_chunks', sa.Column('embedding', sa.Text(), nullable=True))
