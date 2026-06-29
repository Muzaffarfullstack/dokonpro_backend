from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS
from app.core.enums import SubscriptionStatus
from app.core.exceptions import AppException
from app.models import Subscription
from app.modules.subscriptions.repository import SubscriptionsRepository
from app.modules.subscriptions.schemas import (
    SubscriptionActivateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.utils.subscription import subscription_allows_write, subscription_status


class SubscriptionsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SubscriptionsRepository(db)

    async def get_current(self, *, store_id: uuid.UUID) -> SubscriptionResponse:
        subscription = await self._get_subscription(store_id=store_id)
        return self._response(subscription)

    async def activate(
        self,
        *,
        store_id: uuid.UUID,
        payload: SubscriptionActivateRequest,
    ) -> SubscriptionResponse:
        subscription = await self._get_subscription_for_update(store_id=store_id)
        now = datetime.now(UTC)
        subscription.plan = payload.plan.value
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.starts_at = subscription.starts_at or now
        subscription.expires_at = now + timedelta(days=30 * payload.months)
        subscription.max_products = max(subscription.max_products, DEFAULT_MAX_PRODUCTS)
        subscription.max_users = max(subscription.max_users, DEFAULT_MAX_USERS)
        await self.db.commit()
        await self.db.refresh(subscription)
        return self._response(subscription)

    async def cancel(self, *, store_id: uuid.UUID) -> SubscriptionResponse:
        subscription = await self._get_subscription_for_update(store_id=store_id)
        subscription.status = SubscriptionStatus.CANCELLED.value
        await self.db.commit()
        await self.db.refresh(subscription)
        return self._response(subscription)

    async def update(
        self,
        *,
        store_id: uuid.UUID,
        payload: SubscriptionUpdateRequest,
    ) -> SubscriptionResponse:
        subscription = await self._get_subscription_for_update(store_id=store_id)
        if payload.plan is not None:
            subscription.plan = payload.plan.value
        if payload.status is not None:
            subscription.status = payload.status.value
        if payload.trial_ends_at is not None:
            subscription.trial_ends_at = payload.trial_ends_at
        if payload.expires_at is not None:
            subscription.expires_at = payload.expires_at
        if payload.max_products is not None:
            subscription.max_products = payload.max_products
        if payload.max_users is not None:
            subscription.max_users = payload.max_users
        await self.db.commit()
        await self.db.refresh(subscription)
        return self._response(subscription)

    async def _get_subscription(self, *, store_id: uuid.UUID) -> Subscription:
        subscription = await self.repo.get_subscription(store_id=store_id)
        if subscription is None:
            raise AppException(
                code="SUBSCRIPTION_NOT_FOUND",
                message="Tarif topilmadi.",
                status_code=404,
            )
        return subscription

    async def _get_subscription_for_update(self, *, store_id: uuid.UUID) -> Subscription:
        subscription = await self.repo.get_subscription_for_update(store_id=store_id)
        if subscription is None:
            raise AppException(
                code="SUBSCRIPTION_NOT_FOUND",
                message="Tarif topilmadi.",
                status_code=404,
            )
        return subscription

    def _response(self, subscription: Subscription) -> SubscriptionResponse:
        return SubscriptionResponse(
            id=subscription.id,
            store_id=subscription.store_id,
            plan=subscription.plan,
            status=subscription_status(subscription),
            read_only=not subscription_allows_write(subscription),
            starts_at=subscription.starts_at,
            trial_ends_at=subscription.trial_ends_at,
            expires_at=subscription.expires_at,
            max_products=subscription.max_products,
            max_users=subscription.max_users,
        )
