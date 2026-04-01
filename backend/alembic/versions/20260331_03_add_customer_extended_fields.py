"""add customer extended fields

Revision ID: 20260331_03
Revises: 20260331_02
Create Date: 2026-03-31

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_03"
down_revision = "20260331_02"
branch_labels = None
depends_on = None


def upgrade():
    """为 customers 表添加扩展字段"""
    # 公司名称
    op.add_column("customers", sa.Column("company", sa.String(length=200), nullable=True))
    # 职位
    op.add_column("customers", sa.Column("position", sa.String(length=100), nullable=True))
    # 行业
    op.add_column("customers", sa.Column("industry", sa.String(length=100), nullable=True))
    # 成交金额
    op.add_column("customers", sa.Column("deal_value", sa.Float(), nullable=True, server_default="0"))
    # 邮箱
    op.add_column("customers", sa.Column("email", sa.String(length=200), nullable=True))
    # 地址
    op.add_column("customers", sa.Column("address", sa.String(length=500), nullable=True))


def downgrade():
    """删除 customers 表的扩展字段"""
    op.drop_column("customers", "address")
    op.drop_column("customers", "email")
    op.drop_column("customers", "deal_value")
    op.drop_column("customers", "industry")
    op.drop_column("customers", "position")
    op.drop_column("customers", "company")
