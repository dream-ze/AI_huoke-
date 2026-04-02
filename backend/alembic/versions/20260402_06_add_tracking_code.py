"""add tracking_code to published_contents

Revision ID: 20260402_06
Revises: 20260402_05
Create Date: 2026-04-02

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "20260402_06"
down_revision = "20260402_05"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    """检查表是否存在"""
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    if not _table_exists(inspector, table_name):
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    """执行迁移：添加 tracking_code 字段到 published_contents 表"""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # 为 published_contents 表添加 tracking_code 字段
    if _table_exists(inspector, "published_contents"):
        if not _column_exists(inspector, "published_contents", "tracking_code"):
            op.add_column("published_contents", sa.Column("tracking_code", sa.String(100), nullable=True, unique=True))
            # 创建唯一索引
            op.create_index("ix_published_contents_tracking_code", "published_contents", ["tracking_code"], unique=True)


def downgrade():
    """回滚迁移：删除 tracking_code 字段"""
    # 删除索引
    try:
        op.drop_index("ix_published_contents_tracking_code", table_name="published_contents")
    except Exception:
        pass

    # 删除字段
    try:
        op.drop_column("published_contents", "tracking_code")
    except Exception:
        pass
