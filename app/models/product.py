from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import ActiveMixin, BaseEntity, StoreScopedEntity

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.sale import SaleItem
    from app.models.stock_movement import StockMovement
    from app.models.store import Store


class Product(BaseEntity, ActiveMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_products_slug"),
        UniqueConstraint("barcode", name="uq_products_barcode"),
        Index("ix_products_name", "name"),
        Index("ix_products_category", "category_id"),
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(24), default="pcs", nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    category: Mapped[Category | None] = relationship("Category", back_populates="products")
    store_products: Mapped[list[StoreProduct]] = relationship(
        "StoreProduct",
        back_populates="product",
    )


class StoreProduct(StoreScopedEntity, ActiveMixin):
    __tablename__ = "store_products"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_store_products_store_product"),
        UniqueConstraint("store_id", "local_sku", name="uq_store_products_store_local_sku"),
        CheckConstraint("cost_price >= 0", name="cost_price_non_negative"),
        CheckConstraint("sale_price >= 0", name="sale_price_non_negative"),
        CheckConstraint("stock_quantity >= 0", name="stock_quantity_non_negative"),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="low_stock_threshold_non_negative",
        ),
        Index("ix_store_products_store_product", "store_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    local_sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cost_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0"),
        nullable=False,
    )
    low_stock_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0"),
        nullable=False,
    )
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="store_products")
    product: Mapped[Product] = relationship("Product", back_populates="store_products")
    sale_items: Mapped[list[SaleItem]] = relationship("SaleItem", back_populates="store_product")
    stock_movements: Mapped[list[StockMovement]] = relationship(
        "StockMovement",
        back_populates="store_product",
    )


__all__ = ["Product", "StoreProduct"]
