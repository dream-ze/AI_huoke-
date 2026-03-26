"""add structured content tables

Revision ID: 20260324_01
Revises: 20260323_04
Create Date: 2026-03-24 15:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_01"
down_revision = "20260323_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "content_blocks" not in existing_tables:
        op.create_table(
            "content_blocks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("block_type", sa.String(length=32), nullable=False, server_default="paragraph"),
            sa.Column("block_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("block_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_content_blocks_id", "content_blocks", ["id"], unique=False)
        op.create_index("ix_content_blocks_content_id", "content_blocks", ["content_id"], unique=False)

    if "content_comments" not in existing_tables:
        op.create_table(
            "content_comments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_comment_id", sa.Integer(), sa.ForeignKey("content_comments.id", ondelete="SET NULL"), nullable=True),
            sa.Column("commenter_name", sa.String(length=100), nullable=True),
            sa.Column("comment_text", sa.Text(), nullable=False),
            sa.Column("like_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("is_pinned", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_content_comments_id", "content_comments", ["id"], unique=False)
        op.create_index("ix_content_comments_content_id", "content_comments", ["content_id"], unique=False)

    if "content_snapshots" not in existing_tables:
        op.create_table(
            "content_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("raw_html", sa.Text(), nullable=True),
            sa.Column("screenshot_url", sa.String(length=500), nullable=True),
            sa.Column("page_meta_json", sa.JSON(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_content_snapshots_id", "content_snapshots", ["id"], unique=False)
        op.create_index("ix_content_snapshots_content_id", "content_snapshots", ["content_id"], unique=False)

    if "content_insights" not in existing_tables:
        op.create_table(
            "content_insights",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("high_freq_questions_json", sa.JSON(), nullable=True),
            sa.Column("key_sentences_json", sa.JSON(), nullable=True),
            sa.Column("title_pattern", sa.String(length=128), nullable=True),
            sa.Column("suggested_topics_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_content_insights_id", "content_insights", ["id"], unique=False)
        op.create_index("ix_content_insights_content_id", "content_insights", ["content_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "content_insights" in existing_tables:
        op.drop_index("ix_content_insights_content_id", table_name="content_insights")
        op.drop_index("ix_content_insights_id", table_name="content_insights")
        op.drop_table("content_insights")

    if "content_snapshots" in existing_tables:
        op.drop_index("ix_content_snapshots_content_id", table_name="content_snapshots")
        op.drop_index("ix_content_snapshots_id", table_name="content_snapshots")
        op.drop_table("content_snapshots")

    if "content_comments" in existing_tables:
        op.drop_index("ix_content_comments_content_id", table_name="content_comments")
        op.drop_index("ix_content_comments_id", table_name="content_comments")
        op.drop_table("content_comments")

    if "content_blocks" in existing_tables:
        op.drop_index("ix_content_blocks_content_id", table_name="content_blocks")
        op.drop_index("ix_content_blocks_id", table_name="content_blocks")
        op.drop_table("content_blocks")
