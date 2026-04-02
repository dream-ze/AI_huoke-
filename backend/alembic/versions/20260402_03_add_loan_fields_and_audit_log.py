"""添加助贷业务字段和审计日志表

Revision ID: 20260402_03
Revises: 20260402_02
Create Date: 2026-04-02

新增内容：
1. customers表添加助贷业务字段：loan_demand_type, expected_amount, occupation, social_security, debt_range, matchable_products, has_business_license
2. 新建audit_logs表用于审计日志持久化
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "20260402_03"
down_revision = "20260402_02"
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
    """执行迁移"""
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # ========== 1. 创建 audit_logs 表 ==========
    if not _table_exists(inspector, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), nullable=True, comment="操作用户ID"),
            sa.Column("action", sa.String(50), nullable=False, comment="操作类型"),
            sa.Column("resource", sa.String(100), nullable=False, comment="资源类型"),
            sa.Column("resource_id", sa.String(100), nullable=True, comment="资源ID"),
            sa.Column("old_value", sa.Text(), nullable=True, comment="变更前的值"),
            sa.Column("new_value", sa.Text(), nullable=True, comment="变更后的值"),
            sa.Column("detail", sa.Text(), nullable=True, comment="详细信息"),
            sa.Column("result", sa.String(20), server_default="success", comment="操作结果"),
            sa.Column("ip_address", sa.String(50), nullable=True, comment="操作IP地址"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), comment="创建时间"),
        )
        op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
        op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
        op.create_index("idx_audit_logs_resource", "audit_logs", ["resource"], unique=False)
        op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    # ========== 2. 为 customers 表添加助贷业务字段 ==========
    if _table_exists(inspector, "customers"):
        loan_columns = [
            ("loan_demand_type", sa.Column("loan_demand_type", sa.String(50), nullable=True, comment="贷款需求类型")),
            (
                "expected_amount",
                sa.Column("expected_amount", sa.Float(), nullable=True, comment="期望贷款金额（万元）"),
            ),
            ("occupation", sa.Column("occupation", sa.String(100), nullable=True, comment="职业身份")),
            ("social_security", sa.Column("social_security", sa.String(50), nullable=True, comment="社保/公积金状态")),
            ("debt_range", sa.Column("debt_range", sa.String(50), nullable=True, comment="负债区间")),
            (
                "matchable_products",
                sa.Column("matchable_products", sa.JSON(), nullable=True, comment="可匹配产品类型列表"),
            ),
            (
                "has_business_license",
                sa.Column(
                    "has_business_license", sa.Boolean(), server_default=sa.text("false"), comment="是否有营业执照"
                ),
            ),
        ]
        for col_name, col_def in loan_columns:
            if not _column_exists(inspector, "customers", col_name):
                op.add_column("customers", col_def)


def downgrade():
    """回滚迁移"""
    # 删除 customers 表新增字段
    columns_to_drop = [
        "has_business_license",
        "matchable_products",
        "debt_range",
        "social_security",
        "occupation",
        "expected_amount",
        "loan_demand_type",
    ]
    for col_name in columns_to_drop:
        try:
            op.drop_column("customers", col_name)
        except Exception:
            pass

    # 删除 audit_logs 表
    try:
        op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    except Exception:
        pass
    try:
        op.drop_index("idx_audit_logs_resource", table_name="audit_logs")
    except Exception:
        pass
    try:
        op.drop_index("idx_audit_logs_user_id", table_name="audit_logs")
    except Exception:
        pass
    try:
        op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    except Exception:
        pass
    try:
        op.drop_table("audit_logs")
    except Exception:
        pass
