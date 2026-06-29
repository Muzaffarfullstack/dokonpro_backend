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

from app.core.database import ActiveMixin, StoreScopedEntity
from app.core.enums import PaymentMethod, sql_values

if TYPE_CHECKING:
    from app.models.store import Store


class ExpenseCategory(StoreScopedEntity, ActiveMixin):
    __tablename__ = "expense_categories"
    __table_args__ = (
        UniqueConstraint("store_id", "name", name="uq_expense_categories_store_name"),
        Index("ix_expense_categories_store_active", "store_id", "is_active"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="expense_categories")
    expenses: Mapped[list[Expense]] = relationship("Expense", back_populates="category")


class Expense(StoreScopedEntity):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            f"payment_method IN ({sql_values(PaymentMethod)})", name="payment_method_valid"
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_expenses_store_spent_at", "store_id", "spent_at"),
        Index("ix_expenses_store_category", "store_id", "category_id"),
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(24),
        default=PaymentMethod.CASH.value,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    spent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    store: Mapped[Store] = relationship("Store", back_populates="expenses")
    category: Mapped[ExpenseCategory | None] = relationship(
        "ExpenseCategory",
        back_populates="expenses",
    )


__all__ = ["Expense", "ExpenseCategory"]
