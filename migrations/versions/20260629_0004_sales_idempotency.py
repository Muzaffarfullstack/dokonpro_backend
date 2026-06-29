"""Add sales idempotency key

Revision ID: 20260629_0004
Revises: 20260629_0003
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260629_0004"
down_revision: str | None = "20260629_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.create_unique_constraint(
        "uq_sales_store_idempotency_key",
        "sales",
        ["store_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sales_store_idempotency_key", "sales", type_="unique")
    op.drop_column("sales", "idempotency_key")
