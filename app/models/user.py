from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import ActiveMixin, BaseEntity
from app.core.enums import UserRole, sql_values

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.store_staff import StoreStaff


class User(BaseEntity, ActiveMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_users_phone"),
        CheckConstraint(f"role IN ({sql_values(UserRole)})", name="role_valid"),
        Index("ix_users_phone_active", "phone", "is_active"),
    )

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(24), default=UserRole.OWNER.value, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    stores: Mapped[list[Store]] = relationship("Store", back_populates="owner")
    staff_memberships: Mapped[list[StoreStaff]] = relationship(
        "StoreStaff",
        back_populates="user",
        cascade="all, delete-orphan",
    )


__all__ = ["User"]
