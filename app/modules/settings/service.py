from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import hash_password, verify_password
from app.models import Store, Subscription, User
from app.modules.settings.repository import SettingsRepository
from app.modules.settings.schemas import (
    AccountSettingsResponse,
    AccountSettingsUpdateRequest,
    BillingPaymentHistoryItem,
    BillingSettingsResponse,
    BillingSubscriptionResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    PasswordChangeRequest,
    SecuritySettingsResponse,
    StoreSettingsUpdateRequest,
)
from app.utils.phone import normalize_phone
from app.utils.slug import slugify
from app.utils.subscription import subscription_allows_write, subscription_status


class SettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SettingsRepository(db)

    async def get_store_settings(self, *, store_id: uuid.UUID) -> Store:
        store = await self.repo.get_store(store_id=store_id)
        if store is None:
            raise AppException(code="STORE_NOT_FOUND", message="Do'kon topilmadi.", status_code=404)
        return store

    async def update_store_settings(
        self,
        *,
        store_id: uuid.UUID,
        payload: StoreSettingsUpdateRequest,
    ) -> Store:
        store = await self.get_store_settings(store_id=store_id)
        if payload.name is not None:
            store.name = payload.name
            store.slug = slugify(payload.name)
        if payload.phone is not None:
            store.phone = payload.phone
        if payload.address is not None:
            store.address = payload.address
        if payload.currency is not None:
            store.currency = payload.currency.upper()
        if payload.timezone is not None:
            store.timezone = payload.timezone

        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def get_account_settings(self, *, user_id: uuid.UUID) -> AccountSettingsResponse:
        user = await self._get_user(user_id=user_id)
        return self._account_response(user)

    async def update_account_settings(
        self,
        *,
        user_id: uuid.UUID,
        payload: AccountSettingsUpdateRequest,
    ) -> AccountSettingsResponse:
        user = await self._get_user(user_id=user_id)
        phone = normalize_phone(payload.phone)
        existing_user = await self.repo.get_user_by_phone(phone=phone)
        if existing_user is not None and existing_user.id != user.id:
            raise AppException(
                code="PHONE_ALREADY_EXISTS",
                message="Bu telefon raqam bilan hisob mavjud.",
                status_code=409,
                field="phone",
            )

        user.full_name = f"{payload.first_name} {payload.last_name}".strip()
        user.email = payload.email
        user.phone = phone
        await self.db.commit()
        await self.db.refresh(user)
        return self._account_response(user)

    async def get_security_settings(self) -> SecuritySettingsResponse:
        return SecuritySettingsResponse(two_factor_enabled=False)

    async def change_password(self, *, user_id: uuid.UUID, payload: PasswordChangeRequest) -> None:
        user = await self._get_user(user_id=user_id)
        if payload.new_password != payload.new_password_confirm:
            raise AppException(
                code="PASSWORD_CONFIRMATION_MISMATCH",
                message="Yangi parol tasdig'i mos emas.",
                status_code=400,
                field="new_password_confirm",
            )
        if not verify_password(payload.current_password, user.password_hash):
            raise AppException(
                code="INVALID_CURRENT_PASSWORD",
                message="Joriy parol noto'g'ri.",
                status_code=400,
                field="current_password",
            )
        user.password_hash = hash_password(payload.new_password)
        await self.db.commit()

    async def get_billing_settings(self, *, store_id: uuid.UUID) -> BillingSettingsResponse:
        subscription = await self.repo.get_subscription(store_id=store_id)
        payments = await self.repo.list_store_payments(store_id=store_id)
        return BillingSettingsResponse(
            subscription=self._billing_subscription(subscription),
            payment_history=[
                BillingPaymentHistoryItem.model_validate(payment) for payment in payments
            ],
        )

    async def get_notification_settings(self) -> NotificationSettingsResponse:
        return NotificationSettingsResponse()

    async def update_notification_settings(
        self,
        payload: NotificationSettingsUpdateRequest,
    ) -> NotificationSettingsResponse:
        return NotificationSettingsResponse.model_validate(payload)

    async def _get_user(self, *, user_id: uuid.UUID) -> User:
        user = await self.repo.get_user(user_id=user_id)
        if user is None:
            raise AppException(
                code="USER_NOT_FOUND",
                message="Foydalanuvchi topilmadi.",
                status_code=404,
            )
        return user

    def _account_response(self, user: User) -> AccountSettingsResponse:
        first_name, _, last_name = user.full_name.partition(" ")
        return AccountSettingsResponse(
            id=user.id,
            first_name=first_name,
            last_name=last_name,
            email=user.email,
            phone=user.phone,
            language="uz",
        )

    def _billing_subscription(
        self,
        subscription: Subscription | None,
    ) -> BillingSubscriptionResponse | None:
        if subscription is None:
            return None
        return BillingSubscriptionResponse(
            plan=subscription.plan,
            status=subscription_status(subscription),
            read_only=not subscription_allows_write(subscription),
            starts_at=subscription.starts_at,
            trial_ends_at=subscription.trial_ends_at,
            expires_at=subscription.expires_at,
            max_products=subscription.max_products,
            max_users=subscription.max_users,
        )
