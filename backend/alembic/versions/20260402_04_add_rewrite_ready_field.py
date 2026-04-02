"""add rewrite_ready field to inbox and material items

Revision ID: 20260402_04
Revises: 20260402_03
Create Date: 2026-04-02

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = "20260402_04"
down_revision = "20260402_03"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # 添加 rewrite_ready 字段到 mvp_inbox_items 表
    if not _column_exists(inspector, "mvp_inbox_items", "rewrite_ready"):
        op.add_column("mvp_inbox_items", sa.Column("rewrite_ready", sa.Boolean(), nullable=False, server_default="0"))

    # 添加 rewrite_ready 字段到 mvp_material_items 表
    if not _column_exists(inspector, "mvp_material_items", "rewrite_ready"):
        op.add_column(
            "mvp_material_items", sa.Column("rewrite_ready", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    # 回滚：移除 rewrite_ready 字段
    op.drop_column("mvp_material_items", "rewrite_ready")
    op.drop_column("mvp_inbox_items", "rewrite_ready")
