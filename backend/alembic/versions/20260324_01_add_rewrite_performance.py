"""add rewrite_performance table

Revision ID: 20260324_01
Revises: 20260323_04_add_user_wecom_userid
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260324_01"
down_revision = "20260323_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rewrite_performance",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("source_content_id", sa.Integer(), sa.ForeignKey("content_assets.id"), nullable=True, index=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("rewrite_style", sa.String(64), nullable=True),
        sa.Column("rewritten_content", sa.Text(), nullable=False),
        sa.Column("predicted_engagement", sa.Float(), nullable=True),
        sa.Column("predicted_conversion", sa.Float(), nullable=True),
        sa.Column("actual_views", sa.Integer(), nullable=True),
        sa.Column("actual_likes", sa.Integer(), nullable=True),
        sa.Column("actual_comments", sa.Integer(), nullable=True),
        sa.Column("actual_shares", sa.Integer(), nullable=True),
        sa.Column("actual_conversions", sa.Integer(), nullable=True),
        sa.Column("effectiveness_score", sa.Float(), nullable=True),
        sa.Column("publish_metrics", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("rewrite_performance")
