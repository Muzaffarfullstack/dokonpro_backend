from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Payment, Store, Subscription, User


class SettingsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_store(self, *, store_id: uuid.UUID) -> Store | None:
        result = await self.db.execute(
            select(Store).where(Store.id == store_id, Store.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_user(self, *, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_user_by_phone(self, *, phone: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_subscription(self, *, store_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def list_store_payments(self, *, store_id: uuid.UUID) -> Sequence[Payment]:
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.sale), selectinload(Payment.debt_transaction))
            .where(Payment.store_id == store_id)
            .order_by(Payment.paid_at.desc())
            .limit(20)
        )
        return result.scalars().all()
