"""添加pgvector HNSW索引提升向量检索性能

Revision ID: 20260401_01
Revises: 20260331_08
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20260401_01"
down_revision = "20260331_08"
branch_labels = None
depends_on = None


def upgrade():
    """添加HNSW索引优化向量检索性能"""
    # 为知识块embedding字段创建HNSW索引
    # HNSW (Hierarchical Navigable Small World) 是一种高效的近似最近邻搜索算法
    # m = 16: 每个节点的最大连接数
    # ef_construction = 64: 构建时的搜索宽度
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mvp_knowledge_chunks_embedding_hnsw 
        ON mvp_knowledge_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    """
    )

    # 添加普通索引优化knowledge_id查询
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_mvp_knowledge_chunks_knowledge_id 
        ON mvp_knowledge_chunks (knowledge_id);
    """
    )


def downgrade():
    """移除HNSW索引"""
    op.execute("DROP INDEX IF EXISTS ix_mvp_knowledge_chunks_embedding_hnsw;")
    op.execute("DROP INDEX IF EXISTS ix_mvp_knowledge_chunks_knowledge_id;")
