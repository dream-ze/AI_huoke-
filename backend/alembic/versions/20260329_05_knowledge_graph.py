"""知识图谱关系表

Revision ID: 20260329_05
Revises: 20260329_04
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260329_05'
down_revision = '20260329_04'
branch_labels = None
depends_on = None


def upgrade():
    # 创建知识条目关系表
    op.create_table(
        'mvp_knowledge_relations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float(), server_default='0.5'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['source_id'], ['mvp_knowledge_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['mvp_knowledge_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'target_id', 'relation_type', name='uq_knowledge_relation_source_target_type')
    )
    op.create_index('ix_mvp_knowledge_relations_source_id', 'mvp_knowledge_relations', ['source_id'])
    op.create_index('ix_mvp_knowledge_relations_target_id', 'mvp_knowledge_relations', ['target_id'])
    op.create_index('ix_mvp_knowledge_relations_relation_type', 'mvp_knowledge_relations', ['relation_type'])


def downgrade():
    op.drop_index('ix_mvp_knowledge_relations_relation_type', 'mvp_knowledge_relations')
    op.drop_index('ix_mvp_knowledge_relations_target_id', 'mvp_knowledge_relations')
    op.drop_index('ix_mvp_knowledge_relations_source_id', 'mvp_knowledge_relations')
    op.drop_table('mvp_knowledge_relations')
