"""Initial schema

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260628_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
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
    ]


def id_column() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False)


def store_id_column() -> sa.Column:
    return sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        id_column(),
        *timestamps(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'manager', 'cashier')", name=op.f("ck_users_role_valid")
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
    )
    op.create_index("ix_users_phone_active", "users", ["phone", "is_active"], unique=False)

    op.create_table(
        "categories",
        id_column(),
        *timestamps(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent", "categories", ["parent_id"], unique=False)

    op.create_table(
        "products",
        id_column(),
        *timestamps(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_products_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("barcode", name="uq_products_barcode"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_index("ix_products_category", "products", ["category_id"], unique=False)
    op.create_index("ix_products_name", "products", ["name"], unique=False)

    op.create_table(
        "stores",
        id_column(),
        *timestamps(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_stores_owner_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stores"),
        sa.UniqueConstraint("owner_id", "slug", name="uq_stores_owner_slug"),
    )
    op.create_index("ix_stores_owner_active", "stores", ["owner_id", "is_active"], unique=False)
    op.create_index("ix_stores_owner_id", "stores", ["owner_id"], unique=False)

    op.create_table(
        "subscriptions",
        id_column(),
        *timestamps(),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_products", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "max_products >= 0",
            name=op.f("ck_subscriptions_max_products_non_negative"),
        ),
        sa.CheckConstraint("max_users >= 0", name=op.f("ck_subscriptions_max_users_non_negative")),
        sa.CheckConstraint(
            "plan IN ('free', 'pro', 'business')", name=op.f("ck_subscriptions_plan_valid")
        ),
        sa.CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'cancelled', 'expired')",
            name=op.f("ck_subscriptions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_subscriptions_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint("store_id", name="uq_subscriptions_store_id"),
    )
    op.create_index(
        "ix_subscriptions_store_status",
        "subscriptions",
        ["store_id", "status"],
        unique=False,
    )

    op.create_table(
        "store_products",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_sku", sa.String(length=80), nullable=True),
        sa.Column("cost_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("sale_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("stock_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("low_stock_threshold", sa.Numeric(14, 3), nullable=False),
        sa.CheckConstraint(
            "cost_price >= 0", name=op.f("ck_store_products_cost_price_non_negative")
        ),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name=op.f("ck_store_products_low_stock_threshold_non_negative"),
        ),
        sa.CheckConstraint(
            "sale_price >= 0", name=op.f("ck_store_products_sale_price_non_negative")
        ),
        sa.CheckConstraint(
            "stock_quantity >= 0",
            name=op.f("ck_store_products_stock_quantity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_store_products_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_store_products_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_store_products"),
        sa.UniqueConstraint("store_id", "local_sku", name="uq_store_products_store_local_sku"),
        sa.UniqueConstraint("store_id", "product_id", name="uq_store_products_store_product"),
    )
    op.create_index("ix_store_products_store_id", "store_products", ["store_id"], unique=False)
    op.create_index(
        "ix_store_products_store_product",
        "store_products",
        ["store_id", "product_id"],
        unique=False,
    )

    op.create_table(
        "sales",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("payment_status", sa.String(length=24), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("change_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "sold_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "discount_total >= 0", name=op.f("ck_sales_discount_total_non_negative")
        ),
        sa.CheckConstraint("paid_amount >= 0", name=op.f("ck_sales_paid_amount_non_negative")),
        sa.CheckConstraint(
            "payment_status IN ('unpaid', 'partial', 'paid', 'refunded')",
            name=op.f("ck_sales_payment_status_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'completed', 'cancelled', 'refunded')",
            name=op.f("ck_sales_status_valid"),
        ),
        sa.CheckConstraint("subtotal >= 0", name=op.f("ck_sales_subtotal_non_negative")),
        sa.CheckConstraint("total_amount >= 0", name=op.f("ck_sales_total_amount_non_negative")),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_sales_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
    )
    op.create_index("ix_sales_store_id", "sales", ["store_id"], unique=False)
    op.create_index("ix_sales_store_sold_at", "sales", ["store_id", "sold_at"], unique=False)
    op.create_index("ix_sales_store_status", "sales", ["store_id", "status"], unique=False)

    op.create_table(
        "debtors",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("balance >= 0", name=op.f("ck_debtors_balance_non_negative")),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_debtors_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_debtors"),
        sa.UniqueConstraint("store_id", "phone", name="uq_debtors_store_phone"),
    )
    op.create_index("ix_debtors_store_id", "debtors", ["store_id"], unique=False)
    op.create_index("ix_debtors_store_name", "debtors", ["store_id", "name"], unique=False)

    op.create_table(
        "sale_items",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=180), nullable=False),
        sa.Column("local_sku", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint(
            "discount_amount >= 0",
            name=op.f("ck_sale_items_discount_amount_non_negative"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_sale_items_quantity_positive")),
        sa.CheckConstraint(
            "total_amount >= 0", name=op.f("ck_sale_items_total_amount_non_negative")
        ),
        sa.CheckConstraint("unit_price >= 0", name=op.f("ck_sale_items_unit_price_non_negative")),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_sale_items_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_sale_items_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_product_id"],
            ["store_products.id"],
            name="fk_sale_items_store_product_id_store_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_items"),
    )
    op.create_index("ix_sale_items_store_id", "sale_items", ["store_id"], unique=False)
    op.create_index(
        "ix_sale_items_store_product",
        "sale_items",
        ["store_id", "store_product_id"],
        unique=False,
    )
    op.create_index("ix_sale_items_store_sale", "sale_items", ["store_id", "sale_id"], unique=False)

    op.create_table(
        "stock_movements",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("store_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("movement_type", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "moved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "movement_type IN ('in', 'out', 'adjustment', 'return')",
            name=op.f("ck_stock_movements_movement_type_valid"),
        ),
        sa.CheckConstraint("quantity <> 0", name=op.f("ck_stock_movements_quantity_non_zero")),
        sa.CheckConstraint(
            "unit_cost >= 0", name=op.f("ck_stock_movements_unit_cost_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_stock_movements_sale_id_sales",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_stock_movements_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_product_id"],
            ["store_products.id"],
            name="fk_stock_movements_store_product_id_store_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
    )
    op.create_index("ix_stock_movements_store_id", "stock_movements", ["store_id"], unique=False)
    op.create_index(
        "ix_stock_movements_store_moved_at",
        "stock_movements",
        ["store_id", "moved_at"],
        unique=False,
    )
    op.create_index(
        "ix_stock_movements_store_product",
        "stock_movements",
        ["store_id", "store_product_id"],
        unique=False,
    )

    op.create_table(
        "debt_transactions",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("debtor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=24), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "transaction_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_debt_transactions_amount_positive")),
        sa.CheckConstraint(
            "transaction_type IN ('borrow', 'repayment', 'adjustment')",
            name=op.f("ck_debt_transactions_transaction_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["debtor_id"],
            ["debtors.id"],
            name="fk_debt_transactions_debtor_id_debtors",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_debt_transactions_sale_id_sales",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_debt_transactions_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_debt_transactions"),
    )
    op.create_index(
        "ix_debt_transactions_store_id", "debt_transactions", ["store_id"], unique=False
    )
    op.create_index(
        "ix_debt_transactions_store_created",
        "debt_transactions",
        ["store_id", "transaction_at"],
        unique=False,
    )
    op.create_index(
        "ix_debt_transactions_store_debtor",
        "debt_transactions",
        ["store_id", "debtor_id"],
        unique=False,
    )

    op.create_table(
        "payments",
        id_column(),
        *timestamps(),
        store_id_column(),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("debt_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("method", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "paid_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_payments_amount_positive")),
        sa.CheckConstraint(
            "method IN ('cash', 'card', 'transfer', 'click', 'payme', 'other')",
            name=op.f("ck_payments_method_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'refunded')",
            name=op.f("ck_payments_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["debt_transaction_id"],
            ["debt_transactions.id"],
            name="fk_payments_debt_transaction_id_debt_transactions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_payments_sale_id_sales",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            name="fk_payments_store_id_stores",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_store_id", "payments", ["store_id"], unique=False)
    op.create_index("ix_payments_store_paid_at", "payments", ["store_id", "paid_at"], unique=False)
    op.create_index("ix_payments_store_sale", "payments", ["store_id", "sale_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_payments_store_sale", table_name="payments")
    op.drop_index("ix_payments_store_paid_at", table_name="payments")
    op.drop_index("ix_payments_store_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_debt_transactions_store_debtor", table_name="debt_transactions")
    op.drop_index("ix_debt_transactions_store_created", table_name="debt_transactions")
    op.drop_index("ix_debt_transactions_store_id", table_name="debt_transactions")
    op.drop_table("debt_transactions")

    op.drop_index("ix_stock_movements_store_product", table_name="stock_movements")
    op.drop_index("ix_stock_movements_store_moved_at", table_name="stock_movements")
    op.drop_index("ix_stock_movements_store_id", table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_sale_items_store_sale", table_name="sale_items")
    op.drop_index("ix_sale_items_store_product", table_name="sale_items")
    op.drop_index("ix_sale_items_store_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_debtors_store_name", table_name="debtors")
    op.drop_index("ix_debtors_store_id", table_name="debtors")
    op.drop_table("debtors")

    op.drop_index("ix_sales_store_status", table_name="sales")
    op.drop_index("ix_sales_store_sold_at", table_name="sales")
    op.drop_index("ix_sales_store_id", table_name="sales")
    op.drop_table("sales")

    op.drop_index("ix_store_products_store_product", table_name="store_products")
    op.drop_index("ix_store_products_store_id", table_name="store_products")
    op.drop_table("store_products")

    op.drop_index("ix_subscriptions_store_status", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_stores_owner_id", table_name="stores")
    op.drop_index("ix_stores_owner_active", table_name="stores")
    op.drop_table("stores")

    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_categories_parent", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_users_phone_active", table_name="users")
    op.drop_table("users")
