"""add steamspy_owners to games_catalog

Revision ID: d4a9b1c3e028
Revises: c3f1d84a2e17
Create Date: 2026-10-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4a9b1c3e028'
down_revision = 'c3f1d84a2e17'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('games_catalog', sa.Column('steamspy_owners', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('games_catalog', 'steamspy_owners')
