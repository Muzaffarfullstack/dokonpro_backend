from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Store, Subscription


class StoresRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_store(self, *, owner_id: uuid.UUID, store_id: uuid.UUID) -> Store | None:
        result = await self.db.execute(
            select(Store)
            .options(selectinload(Store.subscription))
            .where(Store.id == store_id, Store.owner_id == owner_id, Store.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_store_by_slug(self, *, owner_id: uuid.UUID, slug: str) -> Store | None:
        result = await self.db.execute(
            select(Store).where(
                Store.owner_id == owner_id,
                Store.slug == slug,
                Store.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def _stores_query(self, *, owner_id: uuid.UUID) -> Select[tuple[Store]]:
        return (
            select(Store)
            .options(selectinload(Store.subscription))
            .where(Store.owner_id == owner_id, Store.is_active.is_(True))
        )

    async def list_stores(self, *, owner_id: uuid.UUID) -> Sequence[Store]:
        result = await self.db.execute(self._stores_query(owner_id=owner_id).order_by(Store.name))
        return result.scalars().all()

    async def count_stores(self, *, owner_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(self._stores_query(owner_id=owner_id).subquery())
        )
        return int(result.scalar_one())

    async def create_store(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        slug: str,
        phone: str | None,
        address: str | None,
        currency: str,
        timezone: str,
    ) -> Store:
        store = Store(
            owner_id=owner_id,
            name=name,
            slug=slug,
            phone=phone,
            address=address,
            currency=currency,
            timezone=timezone,
        )
        self.db.add(store)
        await self.db.flush()
        return store

    async def create_subscription(
        self,
        *,
        store_id: uuid.UUID,
        plan: str,
        status: str,
        starts_at: datetime,
        trial_ends_at: datetime,
        max_products: int,
        max_users: int,
    ) -> Subscription:
        subscription = Subscription(
            store_id=store_id,
            plan=plan,
            status=status,
            starts_at=starts_at,
            trial_ends_at=trial_ends_at,
            max_products=max_products,
            max_users=max_users,
        )
        self.db.add(subscription)
        await self.db.flush()
        return subscription
