"""Inventory expiry date and store slug constraint

Revision ID: 20260629_0003
Revises: 20260628_0002
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260629_0003"
down_revision: str | None = "20260628_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("store_products", sa.Column("expiry_date", sa.Date(), nullable=True))
    op.create_unique_constraint("uq_stores_owner_slug", "stores", ["owner_id", "slug"])


def downgrade() -> None:
    op.drop_constraint("uq_stores_owner_slug", "stores", type_="unique")
    op.drop_column("store_products", "expiry_date")
