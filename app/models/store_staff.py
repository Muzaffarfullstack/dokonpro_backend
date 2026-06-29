from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import ActiveMixin, StoreScopedEntity
from app.core.enums import UserRole, sql_values

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.user import User


class StoreStaff(StoreScopedEntity, ActiveMixin):
    __tablename__ = "store_staff"
    __table_args__ = (
        UniqueConstraint("store_id", "user_id", name="uq_store_staff_store_user"),
        CheckConstraint(f"role IN ({sql_values(UserRole)})", name="role_valid"),
        Index("ix_store_staff_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(24), nullable=False)

    store: Mapped[Store] = relationship("Store", back_populates="staff_members")
    user: Mapped[User] = relationship("User", back_populates="staff_memberships")


__all__ = ["StoreStaff"]
