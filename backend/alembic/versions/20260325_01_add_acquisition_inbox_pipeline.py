"""add acquisition inbox pipeline tables

Revision ID: 20260325_01
Revises: 20260324_01
Create Date: 2026-03-25 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260325_01"
down_revision = "20260324_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "collect_tasks" not in existing_tables:
        op.create_table(
            "collect_tasks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("task_type", sa.String(length=30), nullable=False, server_default="keyword"),
            sa.Column("platform", sa.String(length=30), nullable=False),
            sa.Column("keyword", sa.String(length=255), nullable=False),
            sa.Column("max_items", sa.Integer(), nullable=False, server_default="20"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_collect_tasks_id", "collect_tasks", ["id"], unique=False)
        op.create_index("ix_collect_tasks_owner_id", "collect_tasks", ["owner_id"], unique=False)

    if "employee_link_submissions" not in existing_tables:
        op.create_table(
            "employee_link_submissions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("source_type", sa.String(length=30), nullable=False),
            sa.Column("platform", sa.String(length=30), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_employee_link_submissions_id", "employee_link_submissions", ["id"], unique=False)
        op.create_index("ix_employee_link_submissions_owner_id", "employee_link_submissions", ["owner_id"], unique=False)
        op.create_index("ix_employee_link_submissions_employee_id", "employee_link_submissions", ["employee_id"], unique=False)

    if "material_inbox" not in existing_tables:
        op.create_table(
            "material_inbox",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("source_channel", sa.String(length=30), nullable=False),
            sa.Column("source_task_id", sa.Integer(), sa.ForeignKey("collect_tasks.id"), nullable=True),
            sa.Column("source_submission_id", sa.Integer(), sa.ForeignKey("employee_link_submissions.id"), nullable=True),
            sa.Column("platform", sa.String(length=30), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("author", sa.String(length=255), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("cover_url", sa.String(length=500), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("comment_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("collect_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("share_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("publish_time", sa.DateTime(), nullable=True),
            sa.Column("raw_data", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("submitted_by_employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_material_inbox_id", "material_inbox", ["id"], unique=False)
        op.create_index("ix_material_inbox_owner_id", "material_inbox", ["owner_id"], unique=False)
        op.create_index("ix_material_inbox_source_task_id", "material_inbox", ["source_task_id"], unique=False)
        op.create_index("ix_material_inbox_source_submission_id", "material_inbox", ["source_submission_id"], unique=False)
        op.create_index("ix_material_inbox_submitted_by_employee_id", "material_inbox", ["submitted_by_employee_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "material_inbox" in existing_tables:
        op.drop_index("ix_material_inbox_submitted_by_employee_id", table_name="material_inbox")
        op.drop_index("ix_material_inbox_source_submission_id", table_name="material_inbox")
        op.drop_index("ix_material_inbox_source_task_id", table_name="material_inbox")
        op.drop_index("ix_material_inbox_owner_id", table_name="material_inbox")
        op.drop_index("ix_material_inbox_id", table_name="material_inbox")
        op.drop_table("material_inbox")

    if "employee_link_submissions" in existing_tables:
        op.drop_index("ix_employee_link_submissions_employee_id", table_name="employee_link_submissions")
        op.drop_index("ix_employee_link_submissions_owner_id", table_name="employee_link_submissions")
        op.drop_index("ix_employee_link_submissions_id", table_name="employee_link_submissions")
        op.drop_table("employee_link_submissions")

    if "collect_tasks" in existing_tables:
        op.drop_index("ix_collect_tasks_owner_id", table_name="collect_tasks")
        op.drop_index("ix_collect_tasks_id", table_name="collect_tasks")
        op.drop_table("collect_tasks")
