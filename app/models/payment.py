from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import StoreScopedEntity
from app.core.enums import PaymentMethod, PaymentStatus, sql_values

if TYPE_CHECKING:
    from app.models.debt import DebtTransaction
    from app.models.sale import Sale


class Payment(StoreScopedEntity):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            f"method IN ({sql_values(PaymentMethod)})",
            name="method_valid",
        ),
        CheckConstraint(
            f"status IN ({sql_values(PaymentStatus)})",
            name="status_valid",
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_payments_store_paid_at", "store_id", "paid_at"),
        Index("ix_payments_store_sale", "store_id", "sale_id"),
    )

    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="SET NULL"),
        nullable=True,
    )
    debt_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("debt_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[str] = mapped_column(
        String(24),
        default=PaymentMethod.CASH.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default=PaymentStatus.COMPLETED.value,
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sale: Mapped[Sale | None] = relationship("Sale", back_populates="payments")
    debt_transaction: Mapped[DebtTransaction | None] = relationship(
        "DebtTransaction",
        back_populates="payments",
    )


__all__ = ["Payment"]
