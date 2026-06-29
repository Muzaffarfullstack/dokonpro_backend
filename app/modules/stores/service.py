from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS, TRIAL_DAYS
from app.core.enums import SubscriptionPlan, SubscriptionStatus, UserRole
from app.core.exceptions import AppException
from app.core.security import hash_password
from app.models import Store
from app.modules.stores.repository import StoresRepository
from app.modules.stores.schemas import (
    StoreCreateRequest,
    StoreResponse,
    StoreStaffCreateRequest,
    StoreStaffResponse,
    StoreSubscriptionSummary,
    StoreUpdateRequest,
)
from app.utils.phone import normalize_phone
from app.utils.slug import slugify
from app.utils.subscription import subscription_allows_write, subscription_status


class StoresService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StoresRepository(db)

    async def list_stores(self, *, owner_id: uuid.UUID) -> list[StoreResponse]:
        stores = await self.repo.list_stores(owner_id=owner_id)
        return [self._response(store) for store in stores]

    async def get_store(self, *, owner_id: uuid.UUID, store_id: uuid.UUID) -> StoreResponse:
        return self._response(await self._get_store(owner_id=owner_id, store_id=store_id))

    async def create_store(
        self,
        *,
        owner_id: uuid.UUID,
        payload: StoreCreateRequest,
    ) -> StoreResponse:
        slug = slugify(payload.name)
        if not slug:
            raise AppException(
                code="INVALID_SLUG",
                message="Do'kon nomidan slug yaratib bo'lmadi.",
                status_code=400,
                field="name",
            )
        if await self.repo.get_store_by_slug(owner_id=owner_id, slug=slug):
            raise AppException(
                code="STORE_ALREADY_EXISTS",
                message="Bu nom bilan do'kon mavjud.",
                status_code=409,
                field="name",
            )

        now = datetime.now(UTC)
        store = await self.repo.create_store(
            owner_id=owner_id,
            name=payload.name,
            slug=slug,
            phone=payload.phone,
            address=payload.address,
            currency=payload.currency.upper(),
            timezone=payload.timezone,
        )
        subscription = await self.repo.create_subscription(
            store_id=store.id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.TRIALING.value,
            starts_at=now,
            trial_ends_at=now + timedelta(days=TRIAL_DAYS),
            max_products=DEFAULT_MAX_PRODUCTS,
            max_users=DEFAULT_MAX_USERS,
        )
        store.subscription = subscription
        await self.db.commit()
        return self._response(store)

    async def update_store(
        self,
        *,
        owner_id: uuid.UUID,
        store_id: uuid.UUID,
        payload: StoreUpdateRequest,
    ) -> StoreResponse:
        store = await self._get_store(owner_id=owner_id, store_id=store_id)
        if payload.name is not None and payload.name != store.name:
            slug = slugify(payload.name)
            if not slug:
                raise AppException(
                    code="INVALID_SLUG",
                    message="Do'kon nomidan slug yaratib bo'lmadi.",
                    status_code=400,
                    field="name",
                )
            existing = await self.repo.get_store_by_slug(owner_id=owner_id, slug=slug)
            if existing is not None and existing.id != store.id:
                raise AppException(
                    code="STORE_ALREADY_EXISTS",
                    message="Bu nom bilan do'kon mavjud.",
                    status_code=409,
                    field="name",
                )
            store.name = payload.name
            store.slug = slug

        if payload.phone is not None:
            store.phone = payload.phone
        if payload.address is not None:
            store.address = payload.address
        if payload.currency is not None:
            store.currency = payload.currency.upper()
        if payload.timezone is not None:
            store.timezone = payload.timezone

        await self.db.commit()
        await self.db.refresh(store, attribute_names=["subscription"])
        return self._response(store)

    async def deactivate_store(self, *, owner_id: uuid.UUID, store_id: uuid.UUID) -> None:
        store = await self._get_store(owner_id=owner_id, store_id=store_id)
        if await self.repo.count_stores(owner_id=owner_id) <= 1:
            raise AppException(
                code="LAST_STORE_DELETE_BLOCKED",
                message="Oxirgi faol do'konni o'chirib bo'lmaydi.",
                status_code=409,
            )
        store.is_active = False
        await self.db.commit()

    async def list_staff(
        self, *, owner_id: uuid.UUID, store_id: uuid.UUID
    ) -> list[StoreStaffResponse]:
        await self._get_store(owner_id=owner_id, store_id=store_id)
        staff_members = await self.repo.list_staff(store_id=store_id)
        return [self._staff_response(staff) for staff in staff_members]

    async def add_staff(
        self,
        *,
        owner_id: uuid.UUID,
        store_id: uuid.UUID,
        payload: StoreStaffCreateRequest,
    ) -> StoreStaffResponse:
        store = await self._get_store(owner_id=owner_id, store_id=store_id)
        if payload.role == UserRole.OWNER:
            raise AppException(
                code="INVALID_STAFF_ROLE",
                message="Owner rolini staff sifatida qo'shib bo'lmaydi.",
                status_code=400,
                field="role",
            )

        phone = normalize_phone(payload.phone)
        user = await self.repo.get_user_by_phone(phone)
        if user is None:
            user = await self.repo.create_user(
                full_name=payload.full_name,
                phone=phone,
                password_hash=hash_password(payload.password),
                role=payload.role.value,
            )
        else:
            if user.id == store.owner_id:
                raise AppException(
                    code="OWNER_ALREADY_HAS_STORE",
                    message="Do'kon egasini staff sifatida qo'shib bo'lmaydi.",
                    status_code=409,
                    field="phone",
                )
            user.full_name = payload.full_name
            user.role = payload.role.value

        existing_staff = await self.repo.get_staff(store_id=store_id, user_id=user.id)
        if existing_staff is not None:
            if existing_staff.is_active:
                raise AppException(
                    code="STAFF_ALREADY_EXISTS",
                    message="Bu foydalanuvchi allaqachon staff ro'yxatida.",
                    status_code=409,
                    field="phone",
                )
            existing_staff.is_active = True
            existing_staff.role = payload.role.value
            await self.db.commit()
            await self.db.refresh(existing_staff, attribute_names=["user"])
            return self._staff_response(existing_staff)

        staff = await self.repo.create_staff(
            store_id=store_id,
            user_id=user.id,
            role=payload.role.value,
        )
        await self.db.commit()
        return self._staff_response(staff)

    async def remove_staff(
        self,
        *,
        owner_id: uuid.UUID,
        store_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self._get_store(owner_id=owner_id, store_id=store_id)
        staff = await self.repo.get_staff(store_id=store_id, user_id=user_id)
        if staff is None or not staff.is_active:
            raise AppException(
                code="STAFF_NOT_FOUND",
                message="Staff foydalanuvchi topilmadi.",
                status_code=404,
            )
        staff.is_active = False
        await self.db.commit()

    async def _get_store(self, *, owner_id: uuid.UUID, store_id: uuid.UUID) -> Store:
        store = await self.repo.get_store(owner_id=owner_id, store_id=store_id)
        if store is None:
            raise AppException(code="STORE_NOT_FOUND", message="Do'kon topilmadi.", status_code=404)
        return store

    def _response(self, store: Store) -> StoreResponse:
        subscription = store.subscription
        subscription_response = None
        if subscription is not None:
            subscription_response = StoreSubscriptionSummary(
                plan=subscription.plan,
                status=subscription_status(subscription),
                read_only=not subscription_allows_write(subscription),
                trial_ends_at=subscription.trial_ends_at,
                expires_at=subscription.expires_at,
            )
        return StoreResponse(
            id=store.id,
            owner_id=store.owner_id,
            name=store.name,
            slug=store.slug,
            phone=store.phone,
            address=store.address,
            currency=store.currency,
            timezone=store.timezone,
            is_active=store.is_active,
            subscription=subscription_response,
        )

    def _staff_response(self, staff: object) -> StoreStaffResponse:
        return StoreStaffResponse(
            id=staff.id,
            store_id=staff.store_id,
            user_id=staff.user_id,
            full_name=staff.user.full_name,
            phone=staff.user.phone,
            role=staff.role,
            is_active=staff.is_active,
        )
