"""add platform to price_results

Revision ID: f6c3d5e2a140
Revises: e5b2c4d1f039
Create Date: 2026-11-11 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6c3d5e2a140'
down_revision = 'e5b2c4d1f039'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('price_results', sa.Column('platform', sa.String(), server_default='Steam', nullable=True))
    op.create_index('ix_price_results_platform', 'price_results', ['platform'])


def downgrade():
    op.drop_index('ix_price_results_platform', table_name='price_results')
    op.drop_column('price_results', 'platform')
