from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import ActiveMixin, StoreScopedEntity

if TYPE_CHECKING:
    from app.models.purchase import Purchase
    from app.models.store import Store


class Supplier(StoreScopedEntity, ActiveMixin):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("store_id", "name", name="uq_suppliers_store_name"),
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        Index("ix_suppliers_store_active", "store_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )

    store: Mapped[Store] = relationship("Store", back_populates="suppliers")
    purchases: Mapped[list[Purchase]] = relationship("Purchase", back_populates="supplier")


__all__ = ["Supplier"]
