from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import StoreScopedEntity
from app.core.enums import SalePaymentStatus, SaleStatus, sql_values

if TYPE_CHECKING:
    from app.models.debt import DebtTransaction
    from app.models.payment import Payment
    from app.models.product import StoreProduct
    from app.models.store import Store


class Sale(StoreScopedEntity):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({sql_values(SaleStatus)})",
            name="status_valid",
        ),
        CheckConstraint(
            f"payment_status IN ({sql_values(SalePaymentStatus)})",
            name="payment_status_valid",
        ),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("discount_total >= 0", name="discount_total_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        CheckConstraint("paid_amount >= 0", name="paid_amount_non_negative"),
        UniqueConstraint("store_id", "idempotency_key", name="uq_sales_store_idempotency_key"),
        Index("ix_sales_store_sold_at", "store_id", "sold_at"),
        Index("ix_sales_store_status", "store_id", "status"),
    )

    customer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        default=SaleStatus.COMPLETED.value,
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(24),
        default=SalePaymentStatus.PAID.value,
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    change_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    store: Mapped[Store] = relationship("Store", back_populates="sales")
    items: Mapped[list[SaleItem]] = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="sale")
    debt_transactions: Mapped[list[DebtTransaction]] = relationship(
        "DebtTransaction",
        back_populates="sale",
    )


class SaleItem(StoreScopedEntity):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint(
            "purchase_price_snapshot >= 0",
            name="purchase_price_snapshot_non_negative",
        ),
        CheckConstraint("discount_amount >= 0", name="discount_amount_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        Index("ix_sale_items_store_sale", "store_id", "sale_id"),
        Index("ix_sale_items_store_product", "store_id", "store_product_id"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    local_sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    purchase_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    sale: Mapped[Sale] = relationship("Sale", back_populates="items")
    store_product: Mapped[StoreProduct] = relationship(
        "StoreProduct",
        back_populates="sale_items",
    )


__all__ = ["Sale", "SaleItem"]
