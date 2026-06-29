from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Store, StoreStaff, Subscription, User


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

    async def get_user_by_phone(self, phone: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        full_name: str,
        phone: str,
        password_hash: str,
        role: str,
    ) -> User:
        user = User(
            full_name=full_name,
            phone=phone,
            password_hash=password_hash,
            role=role,
            is_verified=True,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_staff(
        self,
        *,
        store_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StoreStaff | None:
        result = await self.db.execute(
            select(StoreStaff)
            .options(selectinload(StoreStaff.user))
            .where(StoreStaff.store_id == store_id, StoreStaff.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_staff(
        self,
        *,
        store_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> StoreStaff:
        staff = StoreStaff(store_id=store_id, user_id=user_id, role=role)
        self.db.add(staff)
        await self.db.flush()
        await self.db.refresh(staff, attribute_names=["user"])
        return staff

    async def list_staff(self, *, store_id: uuid.UUID) -> Sequence[StoreStaff]:
        result = await self.db.execute(
            select(StoreStaff)
            .options(selectinload(StoreStaff.user))
            .where(StoreStaff.store_id == store_id, StoreStaff.is_active.is_(True))
            .order_by(StoreStaff.created_at.asc())
        )
        return result.scalars().all()
