"""Auth phone-only constraints

Revision ID: 20260628_0002
Revises: 20260628_0001
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260628_0002"
down_revision: str | None = "20260628_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_constraint("uq_stores_owner_slug", "stores", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_stores_owner_slug", "stores", ["owner_id", "slug"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])
