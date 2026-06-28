from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DEFAULT_CURRENCY, DEFAULT_TIMEZONE
from app.core.database import ActiveMixin, BaseEntity

if TYPE_CHECKING:
    from app.models.debt import Debtor
    from app.models.product import StoreProduct
    from app.models.sale import Sale
    from app.models.subscription import Subscription
    from app.models.user import User


class Store(BaseEntity, ActiveMixin):
    __tablename__ = "stores"
    __table_args__ = (
        UniqueConstraint("owner_id", "slug", name="uq_stores_owner_slug"),
        Index("ix_stores_owner_active", "owner_id", "is_active"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default=DEFAULT_CURRENCY, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIMEZONE, nullable=False)

    owner: Mapped[User] = relationship("User", back_populates="stores")
    store_products: Mapped[list[StoreProduct]] = relationship(
        "StoreProduct",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    sales: Mapped[list[Sale]] = relationship(
        "Sale",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    debtors: Mapped[list[Debtor]] = relationship(
        "Debtor",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    subscription: Mapped[Subscription | None] = relationship(
        "Subscription",
        back_populates="store",
        cascade="all, delete-orphan",
        uselist=False,
    )


__all__ = ["Store"]
