from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subscription


class SubscriptionsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_subscription(self, *, store_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def get_subscription_for_update(self, *, store_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.store_id == store_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()
