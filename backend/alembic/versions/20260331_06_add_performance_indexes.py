"""添加性能优化索引

Revision ID: 20260331_06
Revises: 20260331_05
Create Date: 2026-03-31
"""

from alembic import op

revision = "20260331_06"
down_revision = "20260331_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MvpKnowledgeItem 索引
    op.create_index("idx_knowledge_platform_audience_topic", "mvp_knowledge_items", ["platform", "audience", "topic"])
    op.create_index("idx_knowledge_library_type_created", "mvp_knowledge_items", ["library_type", "created_at"])
    op.create_index("idx_knowledge_is_hot_platform", "mvp_knowledge_items", ["is_hot", "platform"])

    # MvpInboxItem 索引
    op.create_index("idx_inbox_platform_created", "mvp_inbox_items", ["platform", "created_at"])

    # MvpMaterialItem 索引
    op.create_index("idx_material_platform", "mvp_material_items", ["platform"])
    op.create_index("idx_material_created", "mvp_material_items", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_material_created", "mvp_material_items")
    op.drop_index("idx_material_platform", "mvp_material_items")
    op.drop_index("idx_inbox_platform_created", "mvp_inbox_items")
    op.drop_index("idx_knowledge_is_hot_platform", "mvp_knowledge_items")
    op.drop_index("idx_knowledge_library_type_created", "mvp_knowledge_items")
    op.drop_index("idx_knowledge_platform_audience_topic", "mvp_knowledge_items")
