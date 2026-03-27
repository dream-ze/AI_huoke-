"""add material knowledge pipeline tables

Revision ID: 20260327_02
Revises: 20260327_01
Create Date: 2026-03-27 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_02"
down_revision = "20260327_01"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "source_contents"):
        op.create_table(
            "source_contents",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("source_channel", sa.String(length=30), nullable=False, server_default="manual_input"),
            sa.Column("source_task_id", sa.Integer(), sa.ForeignKey("collect_tasks.id"), nullable=True),
            sa.Column("source_submission_id", sa.Integer(), sa.ForeignKey("employee_link_submissions.id"), nullable=True),
            sa.Column("submitted_by_employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("source_type", sa.String(length=20), nullable=False, server_default="manual"),
            sa.Column("source_platform", sa.String(length=50), nullable=False),
            sa.Column("source_id", sa.String(length=128), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("keyword", sa.String(length=255), nullable=True),
            sa.Column("raw_title", sa.Text(), nullable=True),
            sa.Column("raw_content", sa.Text(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("author_name", sa.String(length=255), nullable=True),
            sa.Column("cover_url", sa.String(length=500), nullable=True),
            sa.Column("publish_time", sa.DateTime(), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="success"),
            sa.Column("risk_status", sa.String(length=32), nullable=False, server_default="safe"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_source_contents_id", "source_contents", ["id"], unique=False)
        op.create_index("ix_source_contents_owner_id", "source_contents", ["owner_id"], unique=False)
        op.create_index("ix_source_contents_source_channel", "source_contents", ["source_channel"], unique=False)
        op.create_index("ix_source_contents_source_platform", "source_contents", ["source_platform"], unique=False)
        op.create_index("ix_source_contents_source_task_id", "source_contents", ["source_task_id"], unique=False)
        op.create_index("ix_source_contents_source_submission_id", "source_contents", ["source_submission_id"], unique=False)
        op.create_index("ix_source_contents_submitted_by_employee_id", "source_contents", ["submitted_by_employee_id"], unique=False)
        op.create_index("ix_source_contents_source_id", "source_contents", ["source_id"], unique=False)
        op.create_index("ix_source_contents_keyword", "source_contents", ["keyword"], unique=False)

    if not _has_table(inspector, "normalized_contents"):
        op.create_table(
            "normalized_contents",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("source_content_id", sa.Integer(), sa.ForeignKey("source_contents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("content_preview", sa.Text(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("source_id", sa.String(length=128), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("author_name", sa.String(length=255), nullable=True),
            sa.Column("cover_url", sa.String(length=500), nullable=True),
            sa.Column("publish_time", sa.DateTime(), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="success"),
            sa.Column("risk_status", sa.String(length=32), nullable=False, server_default="safe"),
            sa.Column("keyword", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_normalized_contents_id", "normalized_contents", ["id"], unique=False)
        op.create_index("ix_normalized_contents_owner_id", "normalized_contents", ["owner_id"], unique=False)
        op.create_index("ix_normalized_contents_source_content_id", "normalized_contents", ["source_content_id"], unique=False)
        op.create_index("ix_normalized_contents_content_hash", "normalized_contents", ["content_hash"], unique=False)
        op.create_index("ix_normalized_contents_platform", "normalized_contents", ["platform"], unique=False)
        op.create_index("ix_normalized_contents_source_id", "normalized_contents", ["source_id"], unique=False)
        op.create_index("ix_normalized_contents_keyword", "normalized_contents", ["keyword"], unique=False)

    if not _has_table(inspector, "material_items"):
        op.create_table(
            "material_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("source_channel", sa.String(length=30), nullable=False, server_default="manual_input"),
            sa.Column("source_task_id", sa.Integer(), sa.ForeignKey("collect_tasks.id"), nullable=True),
            sa.Column("source_submission_id", sa.Integer(), sa.ForeignKey("employee_link_submissions.id"), nullable=True),
            sa.Column("submitted_by_employee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("source_content_id", sa.Integer(), sa.ForeignKey("source_contents.id", ondelete="SET NULL"), nullable=True),
            sa.Column("normalized_content_id", sa.Integer(), sa.ForeignKey("normalized_contents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("source_id", sa.String(length=128), nullable=True),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("keyword", sa.String(length=255), nullable=True),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("content_preview", sa.Text(), nullable=True),
            sa.Column("author_name", sa.String(length=255), nullable=True),
            sa.Column("cover_url", sa.String(length=500), nullable=True),
            sa.Column("publish_time", sa.DateTime(), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("favorite_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hot_level", sa.String(length=10), nullable=False, server_default="low"),
            sa.Column("lead_level", sa.String(length=10), nullable=False, server_default="low"),
            sa.Column("lead_reason", sa.Text(), nullable=True),
            sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("relevance_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="success"),
            sa.Column("risk_status", sa.String(length=32), nullable=False, server_default="safe"),
            sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("filter_reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_material_items_id", "material_items", ["id"], unique=False)
        op.create_index("ix_material_items_owner_id", "material_items", ["owner_id"], unique=False)
        op.create_index("ix_material_items_source_channel", "material_items", ["source_channel"], unique=False)
        op.create_index("ix_material_items_source_task_id", "material_items", ["source_task_id"], unique=False)
        op.create_index("ix_material_items_source_submission_id", "material_items", ["source_submission_id"], unique=False)
        op.create_index("ix_material_items_submitted_by_employee_id", "material_items", ["submitted_by_employee_id"], unique=False)
        op.create_index("ix_material_items_source_content_id", "material_items", ["source_content_id"], unique=False)
        op.create_index("ix_material_items_normalized_content_id", "material_items", ["normalized_content_id"], unique=False)
        op.create_index("ix_material_items_platform", "material_items", ["platform"], unique=False)
        op.create_index("ix_material_items_source_id", "material_items", ["source_id"], unique=False)
        op.create_index("ix_material_items_keyword", "material_items", ["keyword"], unique=False)
        op.create_index("ix_material_items_parse_status", "material_items", ["parse_status"], unique=False)
        op.create_index("ix_material_items_risk_status", "material_items", ["risk_status"], unique=False)
        op.create_index("ix_material_items_is_duplicate", "material_items", ["is_duplicate"], unique=False)
        op.create_index("ix_material_items_status", "material_items", ["status"], unique=False)

    if not _has_table(inspector, "knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("material_item_id", sa.Integer(), sa.ForeignKey("material_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("account_type", sa.String(length=50), nullable=False),
            sa.Column("target_audience", sa.String(length=50), nullable=False),
            sa.Column("content_type", sa.String(length=50), nullable=False),
            sa.Column("topic", sa.Text(), nullable=True),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("content_text", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_knowledge_documents_id", "knowledge_documents", ["id"], unique=False)
        op.create_index("ix_knowledge_documents_owner_id", "knowledge_documents", ["owner_id"], unique=False)
        op.create_index("ix_knowledge_documents_material_item_id", "knowledge_documents", ["material_item_id"], unique=False)
        op.create_index("ix_knowledge_documents_platform", "knowledge_documents", ["platform"], unique=False)
        op.create_index("ix_knowledge_documents_account_type", "knowledge_documents", ["account_type"], unique=False)
        op.create_index("ix_knowledge_documents_target_audience", "knowledge_documents", ["target_audience"], unique=False)
        op.create_index("ix_knowledge_documents_content_type", "knowledge_documents", ["content_type"], unique=False)

    if not _has_table(inspector, "knowledge_chunks"):
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("knowledge_document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_type", sa.String(length=30), nullable=False, server_default="body"),
            sa.Column("chunk_text", sa.Text(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("keywords", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"], unique=False)
        op.create_index("ix_knowledge_chunks_owner_id", "knowledge_chunks", ["owner_id"], unique=False)
        op.create_index("ix_knowledge_chunks_knowledge_document_id", "knowledge_chunks", ["knowledge_document_id"], unique=False)

    if not _has_table(inspector, "rules"):
        op.create_table(
            "rules",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("rule_type", sa.String(length=50), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=True),
            sa.Column("account_type", sa.String(length=50), nullable=True),
            sa.Column("target_audience", sa.String(length=50), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_rules_id", "rules", ["id"], unique=False)
        op.create_index("ix_rules_owner_id", "rules", ["owner_id"], unique=False)
        op.create_index("ix_rules_rule_type", "rules", ["rule_type"], unique=False)
        op.create_index("ix_rules_platform", "rules", ["platform"], unique=False)
        op.create_index("ix_rules_account_type", "rules", ["account_type"], unique=False)
        op.create_index("ix_rules_target_audience", "rules", ["target_audience"], unique=False)

    if not _has_table(inspector, "prompt_templates"):
        op.create_table(
            "prompt_templates",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=True),
            sa.Column("account_type", sa.String(length=50), nullable=True),
            sa.Column("target_audience", sa.String(length=50), nullable=True),
            sa.Column("version", sa.String(length=30), nullable=False, server_default="v1"),
            sa.Column("system_prompt", sa.Text(), nullable=False),
            sa.Column("user_prompt_template", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_prompt_templates_id", "prompt_templates", ["id"], unique=False)
        op.create_index("ix_prompt_templates_owner_id", "prompt_templates", ["owner_id"], unique=False)
        op.create_index("ix_prompt_templates_task_type", "prompt_templates", ["task_type"], unique=False)
        op.create_index("ix_prompt_templates_platform", "prompt_templates", ["platform"], unique=False)
        op.create_index("ix_prompt_templates_account_type", "prompt_templates", ["account_type"], unique=False)
        op.create_index("ix_prompt_templates_target_audience", "prompt_templates", ["target_audience"], unique=False)

    if not _has_table(inspector, "generation_tasks"):
        op.create_table(
            "generation_tasks",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("material_item_id", sa.Integer(), sa.ForeignKey("material_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("account_type", sa.String(length=50), nullable=False),
            sa.Column("target_audience", sa.String(length=50), nullable=False),
            sa.Column("task_type", sa.String(length=50), nullable=False),
            sa.Column("prompt_snapshot", sa.Text(), nullable=True),
            sa.Column("output_text", sa.Text(), nullable=False),
            sa.Column("reference_document_ids", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_generation_tasks_id", "generation_tasks", ["id"], unique=False)
        op.create_index("ix_generation_tasks_owner_id", "generation_tasks", ["owner_id"], unique=False)
        op.create_index("ix_generation_tasks_material_item_id", "generation_tasks", ["material_item_id"], unique=False)
        op.create_index("ix_generation_tasks_platform", "generation_tasks", ["platform"], unique=False)
        op.create_index("ix_generation_tasks_account_type", "generation_tasks", ["account_type"], unique=False)
        op.create_index("ix_generation_tasks_target_audience", "generation_tasks", ["target_audience"], unique=False)
        op.create_index("ix_generation_tasks_task_type", "generation_tasks", ["task_type"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "generation_tasks" in tables:
        for index_name in [
            "ix_generation_tasks_task_type",
            "ix_generation_tasks_target_audience",
            "ix_generation_tasks_account_type",
            "ix_generation_tasks_platform",
            "ix_generation_tasks_material_item_id",
            "ix_generation_tasks_owner_id",
            "ix_generation_tasks_id",
        ]:
            op.drop_index(index_name, table_name="generation_tasks")
        op.drop_table("generation_tasks")

    if "prompt_templates" in tables:
        for index_name in [
            "ix_prompt_templates_target_audience",
            "ix_prompt_templates_account_type",
            "ix_prompt_templates_platform",
            "ix_prompt_templates_task_type",
            "ix_prompt_templates_owner_id",
            "ix_prompt_templates_id",
        ]:
            op.drop_index(index_name, table_name="prompt_templates")
        op.drop_table("prompt_templates")

    if "rules" in tables:
        for index_name in [
            "ix_rules_target_audience",
            "ix_rules_account_type",
            "ix_rules_platform",
            "ix_rules_rule_type",
            "ix_rules_owner_id",
            "ix_rules_id",
        ]:
            op.drop_index(index_name, table_name="rules")
        op.drop_table("rules")

    if "knowledge_chunks" in tables:
        for index_name in [
            "ix_knowledge_chunks_knowledge_document_id",
            "ix_knowledge_chunks_owner_id",
            "ix_knowledge_chunks_id",
        ]:
            op.drop_index(index_name, table_name="knowledge_chunks")
        op.drop_table("knowledge_chunks")

    if "knowledge_documents" in tables:
        for index_name in [
            "ix_knowledge_documents_content_type",
            "ix_knowledge_documents_target_audience",
            "ix_knowledge_documents_account_type",
            "ix_knowledge_documents_platform",
            "ix_knowledge_documents_material_item_id",
            "ix_knowledge_documents_owner_id",
            "ix_knowledge_documents_id",
        ]:
            op.drop_index(index_name, table_name="knowledge_documents")
        op.drop_table("knowledge_documents")

    if "material_items" in tables:
        for index_name in [
            "ix_material_items_status",
            "ix_material_items_is_duplicate",
            "ix_material_items_risk_status",
            "ix_material_items_parse_status",
            "ix_material_items_keyword",
            "ix_material_items_source_id",
            "ix_material_items_platform",
            "ix_material_items_normalized_content_id",
            "ix_material_items_source_content_id",
            "ix_material_items_submitted_by_employee_id",
            "ix_material_items_source_submission_id",
            "ix_material_items_source_task_id",
            "ix_material_items_source_channel",
            "ix_material_items_owner_id",
            "ix_material_items_id",
        ]:
            op.drop_index(index_name, table_name="material_items")
        op.drop_table("material_items")

    if "normalized_contents" in tables:
        for index_name in [
            "ix_normalized_contents_keyword",
            "ix_normalized_contents_source_id",
            "ix_normalized_contents_platform",
            "ix_normalized_contents_content_hash",
            "ix_normalized_contents_source_content_id",
            "ix_normalized_contents_owner_id",
            "ix_normalized_contents_id",
        ]:
            op.drop_index(index_name, table_name="normalized_contents")
        op.drop_table("normalized_contents")

    if "source_contents" in tables:
        for index_name in [
            "ix_source_contents_keyword",
            "ix_source_contents_source_id",
            "ix_source_contents_submitted_by_employee_id",
            "ix_source_contents_source_submission_id",
            "ix_source_contents_source_task_id",
            "ix_source_contents_source_platform",
            "ix_source_contents_source_channel",
            "ix_source_contents_owner_id",
            "ix_source_contents_id",
        ]:
            op.drop_index(index_name, table_name="source_contents")
        op.drop_table("source_contents")