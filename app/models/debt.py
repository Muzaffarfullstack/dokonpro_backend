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
from app.core.enums import DebtTransactionType, sql_values

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.sale import Sale
    from app.models.store import Store


class Debtor(StoreScopedEntity, ActiveMixin):
    __tablename__ = "debtors"
    __table_args__ = (
        UniqueConstraint("store_id", "phone", name="uq_debtors_store_phone"),
        CheckConstraint("balance >= 0", name="balance_non_negative"),
        Index("ix_debtors_store_name", "store_id", "name"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    store: Mapped[Store] = relationship("Store", back_populates="debtors")
    transactions: Mapped[list[DebtTransaction]] = relationship(
        "DebtTransaction",
        back_populates="debtor",
        cascade="all, delete-orphan",
    )


class DebtTransaction(StoreScopedEntity):
    __tablename__ = "debt_transactions"
    __table_args__ = (
        CheckConstraint(
            f"transaction_type IN ({sql_values(DebtTransactionType)})",
            name="transaction_type_valid",
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_debt_transactions_store_debtor", "store_id", "debtor_id"),
        Index("ix_debt_transactions_store_created", "store_id", "transaction_at"),
    )

    debtor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("debtors.id", ondelete="CASCADE"),
        nullable=False,
    )
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(24), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    debtor: Mapped[Debtor] = relationship("Debtor", back_populates="transactions")
    sale: Mapped[Sale | None] = relationship("Sale", back_populates="debt_transactions")
    payments: Mapped[list[Payment]] = relationship("Payment", back_populates="debt_transaction")


__all__ = ["Debtor", "DebtTransaction"]
