from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import StoreScopedEntity
from app.core.enums import StockMovementType, sql_values

if TYPE_CHECKING:
    from app.models.product import StoreProduct


class StockMovement(StoreScopedEntity):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(
            f"movement_type IN ({sql_values(StockMovementType)})",
            name="movement_type_valid",
        ),
        CheckConstraint("quantity <> 0", name="quantity_non_zero"),
        CheckConstraint("unit_cost >= 0", name="unit_cost_non_negative"),
        Index("ix_stock_movements_store_product", "store_id", "store_product_id"),
        Index("ix_stock_movements_store_moved_at", "store_id", "moved_at"),
    )

    store_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("store_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="SET NULL"),
        nullable=True,
    )
    movement_type: Mapped[str] = mapped_column(String(24), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    store_product: Mapped[StoreProduct] = relationship(
        "StoreProduct",
        back_populates="stock_movements",
    )


__all__ = ["StockMovement"]
