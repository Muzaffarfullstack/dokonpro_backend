from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import ActiveMixin, BaseEntity

if TYPE_CHECKING:
    from app.models.product import Product


class Category(BaseEntity, ActiveMixin):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_categories_slug"),
        UniqueConstraint("name", name="uq_categories_name"),
        Index("ix_categories_parent", "parent_id"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side=lambda: [Category.id],
        back_populates="children",
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    products: Mapped[list[Product]] = relationship("Product", back_populates="category")


__all__ = ["Category"]
