"""add steam_appid to games_catalog

Revision ID: c3f1d84a2e17
Revises: b7e3a92c1d05
Create Date: 2026-10-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3f1d84a2e17'
down_revision = 'b7e3a92c1d05'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('games_catalog', sa.Column('steam_appid', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('games_catalog', 'steam_appid')
