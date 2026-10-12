"""schema_cleanup

Revision ID: b7e3a92c1d05
Revises: 0ca11426f028
Create Date: 2026-10-12 12:00:00.000000

Changes:
- games_catalog: drop unused columns url_plati and aliases
- user_tasks: chat_id Integer -> BigInteger (Telegram channel IDs exceed 32-bit range)
- price_results: add indexes on game_id and timestamp for query performance
- user_tasks: add index on game_id
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e3a92c1d05"
down_revision: Union[str, Sequence[str], None] = "0ca11426f028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем неиспользуемые колонки
    op.drop_column("games_catalog", "url_plati")
    op.drop_column("games_catalog", "aliases")

    # chat_id: INTEGER -> BIGINT (Telegram IDs каналов/групп выходят за 32-bit)
    op.alter_column(
        "user_tasks",
        "chat_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # Индексы для ускорения частых запросов
    op.create_index("ix_price_results_game_id", "price_results", ["game_id"])
    op.create_index("ix_price_results_timestamp", "price_results", ["timestamp"])
    op.create_index("ix_user_tasks_game_id", "user_tasks", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_user_tasks_game_id", table_name="user_tasks")
    op.drop_index("ix_price_results_timestamp", table_name="price_results")
    op.drop_index("ix_price_results_game_id", table_name="price_results")

    op.alter_column(
        "user_tasks",
        "chat_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )

    op.add_column("games_catalog", sa.Column("aliases", sa.String(), nullable=True))
    op.add_column("games_catalog", sa.Column("url_plati", sa.String(), nullable=True))
