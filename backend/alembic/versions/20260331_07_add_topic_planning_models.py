"""添加选题规划模型

Revision ID: 20260331_07
Revises: 20260331_06
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op

revision = "20260331_07"
down_revision = "20260331_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建选题计划表
    op.create_table(
        "topic_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("audience", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("content_direction", sa.Text(), nullable=True),
        sa.Column("reference_materials", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_topic_plans_owner_id", "topic_plans", ["owner_id"])

    # 创建选题创意表
    op.create_table(
        "topic_ideas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("topic_plans.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("estimated_engagement", sa.String(20), nullable=True),
        sa.Column("source", sa.String(50), server_default="manual"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_topic_ideas_plan_id", "topic_ideas", ["plan_id"])
    op.create_index("ix_topic_ideas_owner_id", "topic_ideas", ["owner_id"])

    # 创建热门话题表
    op.create_table(
        "hot_topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("heat_score", sa.Float(), server_default="0.0"),
        sa.Column("trend_direction", sa.String(20), server_default="stable"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_hot_topics_platform", "hot_topics", ["platform"])
    op.create_index("idx_hot_topic_platform_heat", "hot_topics", ["platform", "heat_score"])
    op.create_index("idx_hot_topic_discovered", "hot_topics", ["discovered_at"])


def downgrade() -> None:
    op.drop_table("hot_topics")
    op.drop_table("topic_ideas")
    op.drop_table("topic_plans")
