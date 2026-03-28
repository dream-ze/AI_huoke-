"""add mvp core tables for inbox, material, knowledge, generation

Revision ID: mvp_core_001
Revises: 20260328_01
Create Date: 2026-03-28 18:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "mvp_core_001"
down_revision = "20260328_01"
branch_labels = None
depends_on = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. mvp_inbox_items - 收件箱
    if not _has_table(inspector, "mvp_inbox_items"):
        op.create_table(
            "mvp_inbox_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False, server_default="xiaohongshu"),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("author", sa.String(length=200), nullable=True),
            sa.Column("source_url", sa.String(length=1000), nullable=True),
            sa.Column("source_type", sa.String(length=50), nullable=False, server_default="collect"),
            sa.Column("keyword", sa.String(length=200), nullable=True),
            sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
            sa.Column("duplicate_status", sa.String(length=20), nullable=False, server_default="unique"),
            sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("tech_status", sa.String(length=30), nullable=False, server_default="parsed"),
            sa.Column("biz_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_inbox_items_id"), "mvp_inbox_items", ["id"], unique=False)

    # 2. mvp_material_items - 素材库
    if not _has_table(inspector, "mvp_material_items"):
        op.create_table(
            "mvp_material_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_url", sa.String(length=1000), nullable=True),
            sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("author", sa.String(length=200), nullable=True),
            sa.Column("is_hot", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_inbox_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["source_inbox_id"], ["mvp_inbox_items.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_material_items_id"), "mvp_material_items", ["id"], unique=False)

    # 3. mvp_tags - 标签
    if not _has_table(inspector, "mvp_tags"):
        op.create_table(
            "mvp_tags",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", "type", name="uq_mvp_tag_name_type"),
        )
        op.create_index(op.f("ix_mvp_tags_id"), "mvp_tags", ["id"], unique=False)

    # 4. mvp_material_tag_rel - 素材标签关联
    if not _has_table(inspector, "mvp_material_tag_rel"):
        op.create_table(
            "mvp_material_tag_rel",
            sa.Column("material_id", sa.Integer(), nullable=False),
            sa.Column("tag_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["material_id"], ["mvp_material_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tag_id"], ["mvp_tags.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("material_id", "tag_id"),
        )

    # 5. mvp_knowledge_items - 知识库
    if not _has_table(inspector, "mvp_knowledge_items"):
        op.create_table(
            "mvp_knowledge_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=True),
            sa.Column("platform", sa.String(length=50), nullable=True),
            sa.Column("audience", sa.String(length=100), nullable=True),
            sa.Column("style", sa.String(length=100), nullable=True),
            sa.Column("source_material_id", sa.Integer(), nullable=True),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("embedding", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["source_material_id"], ["mvp_material_items.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_knowledge_items_id"), "mvp_knowledge_items", ["id"], unique=False)

    # 6. mvp_prompt_templates - 提示词模板
    if not _has_table(inspector, "mvp_prompt_templates"):
        op.create_table(
            "mvp_prompt_templates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=True),
            sa.Column("audience", sa.String(length=100), nullable=True),
            sa.Column("style", sa.String(length=100), nullable=True),
            sa.Column("template", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_prompt_templates_id"), "mvp_prompt_templates", ["id"], unique=False)

    # 7. mvp_generation_results - 生成结果
    if not _has_table(inspector, "mvp_generation_results"):
        op.create_table(
            "mvp_generation_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_material_id", sa.Integer(), nullable=True),
            sa.Column("input_text", sa.Text(), nullable=False),
            sa.Column("output_title", sa.String(length=500), nullable=True),
            sa.Column("output_text", sa.Text(), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=True),
            sa.Column("audience", sa.String(length=100), nullable=True),
            sa.Column("style", sa.String(length=100), nullable=True),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("compliance_status", sa.String(length=30), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["source_material_id"], ["mvp_material_items.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_generation_results_id"), "mvp_generation_results", ["id"], unique=False)

    # 8. mvp_compliance_rules - 合规规则
    if not _has_table(inspector, "mvp_compliance_rules"):
        op.create_table(
            "mvp_compliance_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rule_type", sa.String(length=50), nullable=False),
            sa.Column("keyword", sa.String(length=200), nullable=False),
            sa.Column("suggestion", sa.Text(), nullable=True),
            sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_mvp_compliance_rules_id"), "mvp_compliance_rules", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 按依赖顺序反向删除
    tables_to_drop = [
        "mvp_compliance_rules",
        "mvp_generation_results",
        "mvp_prompt_templates",
        "mvp_knowledge_items",
        "mvp_material_tag_rel",
        "mvp_tags",
        "mvp_material_items",
        "mvp_inbox_items",
    ]

    for table_name in tables_to_drop:
        if _has_table(inspector, table_name):
            op.drop_table(table_name)
            inspector = sa.inspect(bind)  # 刷新 inspector
