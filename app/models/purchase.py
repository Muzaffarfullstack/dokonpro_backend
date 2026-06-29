from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import StoreScopedEntity
from app.core.enums import PurchaseStatus, sql_values

if TYPE_CHECKING:
    from app.models.product import StoreProduct
    from app.models.store import Store
    from app.models.supplier import Supplier


class Purchase(StoreScopedEntity):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint(f"status IN ({sql_values(PurchaseStatus)})", name="status_valid"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        CheckConstraint("paid_amount >= 0", name="paid_amount_non_negative"),
        Index("ix_purchases_store_purchased_at", "store_id", "purchased_at"),
        Index("ix_purchases_store_supplier", "store_id", "supplier_id"),
    )

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default=PurchaseStatus.COMPLETED.value,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    store: Mapped[Store] = relationship("Store", back_populates="purchases")
    supplier: Mapped[Supplier | None] = relationship("Supplier", back_populates="purchases")
    items: Mapped[list[PurchaseItem]] = relationship(
        "PurchaseItem",
        back_populates="purchase",
        cascade="all, delete-orphan",
    )


class PurchaseItem(StoreScopedEntity):
    __tablename__ = "purchase_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="unit_cost_non_negative"),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
        Index("ix_purchase_items_store_purchase", "store_id", "purchase_id"),
        Index("ix_purchase_items_store_product", "store_id", "store_product_id"),
    )

    purchase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    purchase: Mapped[Purchase] = relationship("Purchase", back_populates="items")
    store_product: Mapped[StoreProduct] = relationship(
        "StoreProduct", back_populates="purchase_items"
    )


__all__ = ["Purchase", "PurchaseItem"]
