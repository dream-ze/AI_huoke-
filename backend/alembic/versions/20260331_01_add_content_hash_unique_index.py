"""add unique index on normalized_contents.content_hash

Revision ID: 20260331_01
Revises: 20260329_06
Create Date: 2026-03-31

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_01"
down_revision = "20260329_06"
branch_labels = None
depends_on = None


def upgrade():
    """
    为 normalized_contents 表的 content_hash 字段添加唯一索引，实现跨任务去重。

    注意：
    - 首先检查是否存在重复数据
    - 如果存在重复，先删除或合并重复数据
    - 然后添加唯一索引
    """
    # 1. 首先检查并删除重复的 content_hash 记录（保留最新的一条）
    op.execute(
        """
        DELETE FROM normalized_contents
        WHERE id NOT IN (
            SELECT DISTINCT ON (content_hash) id
            FROM normalized_contents
            ORDER BY content_hash, created_at DESC
        )
        AND content_hash IS NOT NULL
        AND content_hash != ''
    """
    )

    # 2. 删除现有的普通索引（如果存在）
    op.execute(
        """
        DROP INDEX IF EXISTS ix_normalized_contents_content_hash
    """
    )

    # 3. 创建唯一索引
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_normalized_contents_content_hash
        ON normalized_contents (content_hash)
        WHERE content_hash IS NOT NULL AND content_hash != ''
    """
    )

    # 4. 为 source_contents 表的 source_id 添加索引（辅助去重查询）
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_source_contents_source_id_platform
        ON source_contents (source_id, source_platform)
        WHERE source_id IS NOT NULL
    """
    )


def downgrade():
    """回滚：删除唯一索引，恢复普通索引"""
    # 1. 删除唯一索引
    op.execute(
        """
        DROP INDEX IF EXISTS uq_normalized_contents_content_hash
    """
    )

    # 2. 恢复普通索引
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_normalized_contents_content_hash
        ON normalized_contents (content_hash)
    """
    )

    # 3. 删除辅助索引
    op.execute(
        """
        DROP INDEX IF EXISTS ix_source_contents_source_id_platform
    """
    )
