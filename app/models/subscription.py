from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS
from app.core.database import BaseEntity
from app.core.enums import SubscriptionPlan, SubscriptionStatus, sql_values

if TYPE_CHECKING:
    from app.models.store import Store


class Subscription(BaseEntity):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(f"plan IN ({sql_values(SubscriptionPlan)})", name="plan_valid"),
        CheckConstraint(
            f"status IN ({sql_values(SubscriptionStatus)})",
            name="status_valid",
        ),
        CheckConstraint("max_products >= 0", name="max_products_non_negative"),
        CheckConstraint("max_users >= 0", name="max_users_non_negative"),
        Index("ix_subscriptions_store_status", "store_id", "status"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    plan: Mapped[str] = mapped_column(
        String(24),
        default=SubscriptionPlan.FREE.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default=SubscriptionStatus.TRIALING.value,
        nullable=False,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_products: Mapped[int] = mapped_column(default=DEFAULT_MAX_PRODUCTS, nullable=False)
    max_users: Mapped[int] = mapped_column(default=DEFAULT_MAX_USERS, nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="subscription")


__all__ = ["Subscription"]
