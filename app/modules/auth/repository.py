from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS
from app.core.enums import SubscriptionPlan, SubscriptionStatus, UserRole
from app.models import Store, StoreStaff, Subscription, User


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_user_by_phone(self, phone: str) -> User | None:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(
        self,
        *,
        full_name: str,
        phone: str,
        password_hash: str,
    ) -> User:
        user = User(
            full_name=full_name,
            phone=phone,
            password_hash=password_hash,
            role=UserRole.OWNER.value,
            is_verified=True,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_password(self, *, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        await self.db.flush()
        return user

    async def create_store(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        slug: str,
    ) -> Store:
        store = Store(owner_id=owner_id, name=name, slug=slug)
        self.db.add(store)
        await self.db.flush()
        return store

    async def create_subscription(
        self,
        *,
        store_id: uuid.UUID,
        starts_at: datetime,
        trial_ends_at: datetime,
    ) -> Subscription:
        subscription = Subscription(
            store_id=store_id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.TRIALING.value,
            starts_at=starts_at,
            trial_ends_at=trial_ends_at,
            max_products=DEFAULT_MAX_PRODUCTS,
            max_users=DEFAULT_MAX_USERS,
        )
        self.db.add(subscription)
        await self.db.flush()
        return subscription

    async def list_user_stores(self, user_id: uuid.UUID) -> list[Store]:
        result = await self.db.execute(
            select(Store)
            .options(selectinload(Store.subscription))
            .outerjoin(
                StoreStaff,
                and_(
                    StoreStaff.store_id == Store.id,
                    StoreStaff.user_id == user_id,
                    StoreStaff.is_active.is_(True),
                ),
            )
            .where(
                Store.is_active.is_(True),
                or_(Store.owner_id == user_id, StoreStaff.user_id == user_id),
            )
            .order_by(Store.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_user_store(self, *, user_id: uuid.UUID, store_id: uuid.UUID) -> Store | None:
        result = await self.db.execute(
            select(Store)
            .options(selectinload(Store.subscription))
            .outerjoin(
                StoreStaff,
                and_(
                    StoreStaff.store_id == Store.id,
                    StoreStaff.user_id == user_id,
                    StoreStaff.is_active.is_(True),
                ),
            )
            .where(
                Store.id == store_id,
                Store.is_active.is_(True),
                or_(Store.owner_id == user_id, StoreStaff.user_id == user_id),
            )
        )
        return result.scalar_one_or_none()
