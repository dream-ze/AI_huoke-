"""legacy baseline bridge revision

Revision ID: 20260323_0008
Revises:
Create Date: 2026-03-23 21:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0008"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Compatibility bridge: keep empty so existing databases at this revision
    # can continue migration chain with new revisions tracked in this repo.
    pass


def downgrade() -> None:
    pass
