"""为关键表添加软删除字段

Revision ID: 20260401_02
Revises: 20260401_01
Create Date: 2026-04-01
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20260401_02"
down_revision = "20260401_01"
branch_labels = None
depends_on = None

# 需要添加软删除字段的表列表
TABLES = [
    "customers",
    "leads",
    "mvp_material_items",
    "mvp_knowledge_items",
]


def upgrade():
    """为关键表添加软删除字段"""
    for table_name in TABLES:
        # 检查列是否已存在
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        # 添加 is_deleted 列
        if "is_deleted" not in columns:
            op.add_column(table_name, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"))
            # 创建索引
            op.create_index(f"ix_{table_name}_is_deleted", table_name, ["is_deleted"])

        # 添加 deleted_at 列
        if "deleted_at" not in columns:
            op.add_column(table_name, sa.Column("deleted_at", sa.DateTime(), nullable=True))

        # 添加 deleted_by 列
        if "deleted_by" not in columns:
            op.add_column(table_name, sa.Column("deleted_by", sa.Integer(), nullable=True))

    # 为现有数据设置默认值
    for table_name in TABLES:
        op.execute(f"UPDATE {table_name} SET is_deleted = false WHERE is_deleted IS NULL;")


def downgrade():
    """移除软删除字段"""
    for table_name in TABLES:
        # 检查列是否存在
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        # 删除索引
        if "is_deleted" in columns:
            try:
                op.drop_index(f"ix_{table_name}_is_deleted", table_name=table_name)
            except:
                pass  # 索引可能不存在

        # 删除列
        for col_name in ["deleted_by", "deleted_at", "is_deleted"]:
            if col_name in columns:
                try:
                    op.drop_column(table_name, col_name)
                except:
                    pass  # 列可能不存在
