"""add social_accounts table

Revision ID: 20260331_02
Revises: 20260331_01
Create Date: 2026-03-31

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260331_02"
down_revision = "20260331_01"
branch_labels = None
depends_on = None


def upgrade():
    """创建 social_accounts 表（幂等：若已存在则跳过）"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "social_accounts" not in inspector.get_table_names():
        op.create_table(
            "social_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("account_id", sa.String(length=200), nullable=True),
            sa.Column("account_name", sa.String(length=100), nullable=False),
            sa.Column("avatar_url", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="active", nullable=True),
            sa.Column("followers_count", sa.Integer(), server_default="0", nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(
                ["owner_id"],
                ["users.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )

        # 创建索引
        op.create_index(op.f("ix_social_accounts_id"), "social_accounts", ["id"], unique=False)
        op.create_index(op.f("ix_social_accounts_owner_id"), "social_accounts", ["owner_id"], unique=False)
        op.create_index(op.f("ix_social_accounts_platform"), "social_accounts", ["platform"], unique=False)


def downgrade():
    """删除 social_accounts 表"""
    op.drop_index(op.f("ix_social_accounts_platform"), table_name="social_accounts")
    op.drop_index(op.f("ix_social_accounts_owner_id"), table_name="social_accounts")
    op.drop_index(op.f("ix_social_accounts_id"), table_name="social_accounts")
    op.drop_table("social_accounts")
