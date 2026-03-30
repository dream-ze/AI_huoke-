"""反馈闭环表 - 生成反馈与知识质量评分

Revision ID: 20260329_04
Revises: 20260329_03
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260329_04'
down_revision = '20260329_03'
branch_labels = None
depends_on = None


def upgrade():
    # 创建生成结果反馈表
    op.create_table(
        'mvp_generation_feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('generation_id', sa.String(100), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('generated_text', sa.Text(), nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('modified_text', sa.Text(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_tags', sa.Text(), nullable=True),
        sa.Column('knowledge_ids_used', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mvp_generation_feedback_generation_id', 'mvp_generation_feedback', ['generation_id'])
    op.create_index('ix_mvp_generation_feedback_feedback_type', 'mvp_generation_feedback', ['feedback_type'])
    op.create_index('ix_mvp_generation_feedback_created_at', 'mvp_generation_feedback', ['created_at'])

    # 创建知识库条目质量评分表
    op.create_table(
        'mvp_knowledge_quality_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('knowledge_id', sa.Integer(), nullable=False),
        sa.Column('reference_count', sa.Integer(), server_default='0'),
        sa.Column('positive_feedback', sa.Integer(), server_default='0'),
        sa.Column('negative_feedback', sa.Integer(), server_default='0'),
        sa.Column('neutral_feedback', sa.Integer(), server_default='0'),
        sa.Column('quality_score', sa.Float(), server_default='0.5'),
        sa.Column('weight_boost', sa.Float(), server_default='1.0'),
        sa.Column('last_referenced_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['knowledge_id'], ['mvp_knowledge_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('knowledge_id')
    )
    op.create_index('ix_mvp_knowledge_quality_scores_knowledge_id', 'mvp_knowledge_quality_scores', ['knowledge_id'])


def downgrade():
    op.drop_index('ix_mvp_knowledge_quality_scores_knowledge_id', 'mvp_knowledge_quality_scores')
    op.drop_table('mvp_knowledge_quality_scores')
    
    op.drop_index('ix_mvp_generation_feedback_created_at', 'mvp_generation_feedback')
    op.drop_index('ix_mvp_generation_feedback_feedback_type', 'mvp_generation_feedback')
    op.drop_index('ix_mvp_generation_feedback_generation_id', 'mvp_generation_feedback')
    op.drop_table('mvp_generation_feedback')
