"""add is_free to games_catalog

Revision ID: e5b2c4d1f039
Revises: d4a9b1c3e028
Create Date: 2026-10-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b2c4d1f039'
down_revision = 'd4a9b1c3e028'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('games_catalog', sa.Column('is_free', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('games_catalog', 'is_free')
