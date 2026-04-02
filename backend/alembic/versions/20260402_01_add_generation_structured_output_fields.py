"""为 mvp_generation_results 添加结构化输出字段

Revision ID: 20260402_01
Revises: 20260401_02
Create Date: 2026-04-02

为AI生成结果添加结构化输出字段，使生成结果从"一段文案"升级为"可审核、可对比、可沉淀"的结构化产物。
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "20260402_01"
down_revision = "20260401_02"
branch_labels = None
depends_on = None

TABLE_NAME = "mvp_generation_results"

# 需要添加的结构化输出字段
NEW_COLUMNS = [
    ("opening_hook", sa.Text(), True, "开头钩子"),
    ("cta_section", sa.Text(), True, "行动引导段"),
    ("risk_disclaimer", sa.Text(), True, "风险点说明"),
    ("alternative_v1", sa.Text(), True, "低风险替代版本"),
    ("alternative_v2", sa.Text(), True, "高转化替代版本"),
    ("output_structure", sa.JSON(), True, "完整结构化输出JSON"),
]


def upgrade():
    """添加结构化输出字段"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 检查表是否存在
    tables = inspector.get_table_names()
    if TABLE_NAME not in tables:
        # 表不存在，跳过（可能是由其他迁移创建）
        return

    columns = [col["name"] for col in inspector.get_columns(TABLE_NAME)]

    for col_name, col_type, nullable, comment in NEW_COLUMNS:
        if col_name not in columns:
            op.add_column(TABLE_NAME, sa.Column(col_name, col_type, nullable=nullable, comment=comment))


def downgrade():
    """移除结构化输出字段"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = inspector.get_table_names()
    if TABLE_NAME not in tables:
        return

    columns = [col["name"] for col in inspector.get_columns(TABLE_NAME)]

    for col_name, _, _, _ in NEW_COLUMNS:
        if col_name in columns:
            op.drop_column(TABLE_NAME, col_name)
