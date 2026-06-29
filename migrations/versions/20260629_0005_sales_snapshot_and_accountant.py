"""Add sale item cost snapshot and accountant role

Revision ID: 20260629_0005
Revises: 20260629_0004
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260629_0005"
down_revision: str | None = "20260629_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sale_items",
        sa.Column(
            "purchase_price_snapshot",
            sa.Numeric(14, 2),
            server_default="0",
            nullable=False,
        ),
    )
    op.alter_column("sale_items", "purchase_price_snapshot", server_default=None)
    op.create_check_constraint(
        op.f("ck_sale_items_purchase_price_snapshot_non_negative"),
        "sale_items",
        "purchase_price_snapshot >= 0",
    )

    op.drop_constraint(op.f("ck_users_role_valid"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role_valid"),
        "users",
        "role IN ('owner', 'manager', 'cashier', 'accountant')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_role_valid"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role_valid"),
        "users",
        "role IN ('owner', 'manager', 'cashier')",
    )
    op.drop_constraint(
        op.f("ck_sale_items_purchase_price_snapshot_non_negative"),
        "sale_items",
        type_="check",
    )
    op.drop_column("sale_items", "purchase_price_snapshot")
