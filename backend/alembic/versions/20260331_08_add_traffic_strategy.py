"""添加引流策略模型

Revision ID: 20260331_08
Revises: 20260331_07
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op

revision = "20260331_08"
down_revision = "20260331_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traffic_strategies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("target_audience", sa.String(200), nullable=True),
        sa.Column("cta_template", sa.Text(), nullable=True),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column("performance_metrics", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_traffic_strategies_owner_id", "traffic_strategies", ["owner_id"])
    op.create_index("idx_traffic_owner_platform", "traffic_strategies", ["owner_id", "platform"])
    op.create_index("idx_traffic_status", "traffic_strategies", ["status"])


def downgrade() -> None:
    op.drop_table("traffic_strategies")
