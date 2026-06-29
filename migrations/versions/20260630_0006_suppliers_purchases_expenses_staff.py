"""suppliers purchases expenses staff

Revision ID: 20260630_0006
Revises: 20260629_0005
Create Date: 2026-06-30 00:06:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260630_0006"
down_revision: str | None = "20260629_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("balance >= 0", name=op.f("ck_suppliers_balance_non_negative")),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_suppliers_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("store_id", "name", name="uq_suppliers_store_name"),
    )
    op.create_index(
        "ix_suppliers_store_active", "suppliers", ["store_id", "is_active"], unique=False
    )
    op.create_index(op.f("ix_suppliers_store_id"), "suppliers", ["store_id"], unique=False)

    op.create_table(
        "expense_categories",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_expense_categories_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expense_categories")),
        sa.UniqueConstraint("store_id", "name", name="uq_expense_categories_store_name"),
    )
    op.create_index(
        "ix_expense_categories_store_active",
        "expense_categories",
        ["store_id", "is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_expense_categories_store_id"), "expense_categories", ["store_id"], unique=False
    )

    op.create_table(
        "store_staff",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'manager', 'cashier', 'accountant')",
            name=op.f("ck_store_staff_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_store_staff_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_store_staff_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_store_staff")),
        sa.UniqueConstraint("store_id", "user_id", name="uq_store_staff_store_user"),
    )
    op.create_index(op.f("ix_store_staff_store_id"), "store_staff", ["store_id"], unique=False)
    op.create_index(
        "ix_store_staff_user_active", "store_staff", ["user_id", "is_active"], unique=False
    )

    op.create_table(
        "purchases",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("paid_amount >= 0", name=op.f("ck_purchases_paid_amount_non_negative")),
        sa.CheckConstraint(
            "status IN ('completed', 'cancelled')",
            name=op.f("ck_purchases_status_valid"),
        ),
        sa.CheckConstraint(
            "total_amount >= 0", name=op.f("ck_purchases_total_amount_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_purchases_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_purchases_supplier_id_suppliers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchases")),
    )
    op.create_index(
        "ix_purchases_store_purchased_at", "purchases", ["store_id", "purchased_at"], unique=False
    )
    op.create_index(
        "ix_purchases_store_supplier", "purchases", ["store_id", "supplier_id"], unique=False
    )
    op.create_index(op.f("ix_purchases_store_id"), "purchases", ["store_id"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=24), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "spent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_expenses_amount_positive")),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'card', 'transfer', 'click', 'payme', 'other')",
            name=op.f("ck_expenses_payment_method_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["expense_categories.id"],
            name=op.f("fk_expenses_category_id_expense_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_expenses_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expenses")),
    )
    op.create_index(
        "ix_expenses_store_category", "expenses", ["store_id", "category_id"], unique=False
    )
    op.create_index(
        "ix_expenses_store_spent_at", "expenses", ["store_id", "spent_at"], unique=False
    )
    op.create_index(op.f("ix_expenses_store_id"), "expenses", ["store_id"], unique=False)

    op.create_table(
        "purchase_items",
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=180), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_purchase_items_quantity_positive")),
        sa.CheckConstraint(
            "total_amount >= 0", name=op.f("ck_purchase_items_total_amount_non_negative")
        ),
        sa.CheckConstraint("unit_cost >= 0", name=op.f("ck_purchase_items_unit_cost_non_negative")),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name=op.f("fk_purchase_items_purchase_id_purchases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name=op.f("fk_purchase_items_store_id_stores"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_product_id"],
            ["store_products.id"],
            name=op.f("fk_purchase_items_store_product_id_store_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchase_items")),
    )
    op.create_index(
        "ix_purchase_items_store_product",
        "purchase_items",
        ["store_id", "store_product_id"],
        unique=False,
    )
    op.create_index(
        "ix_purchase_items_store_purchase",
        "purchase_items",
        ["store_id", "purchase_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_items_store_id"), "purchase_items", ["store_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_items_store_id"), table_name="purchase_items")
    op.drop_index("ix_purchase_items_store_purchase", table_name="purchase_items")
    op.drop_index("ix_purchase_items_store_product", table_name="purchase_items")
    op.drop_table("purchase_items")
    op.drop_index(op.f("ix_expenses_store_id"), table_name="expenses")
    op.drop_index("ix_expenses_store_spent_at", table_name="expenses")
    op.drop_index("ix_expenses_store_category", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index(op.f("ix_purchases_store_id"), table_name="purchases")
    op.drop_index("ix_purchases_store_supplier", table_name="purchases")
    op.drop_index("ix_purchases_store_purchased_at", table_name="purchases")
    op.drop_table("purchases")
    op.drop_index("ix_store_staff_user_active", table_name="store_staff")
    op.drop_index(op.f("ix_store_staff_store_id"), table_name="store_staff")
    op.drop_table("store_staff")
    op.drop_index(op.f("ix_expense_categories_store_id"), table_name="expense_categories")
    op.drop_index("ix_expense_categories_store_active", table_name="expense_categories")
    op.drop_table("expense_categories")
    op.drop_index(op.f("ix_suppliers_store_id"), table_name="suppliers")
    op.drop_index("ix_suppliers_store_active", table_name="suppliers")
    op.drop_table("suppliers")
