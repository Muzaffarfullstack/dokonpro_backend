import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.enums import SubscriptionPlan, SubscriptionStatus
from app.core.exceptions import AppException
from app.models import Subscription
from app.modules.subscriptions.schemas import SubscriptionActivateRequest, SubscriptionUpdateRequest
from app.modules.subscriptions.service import SubscriptionsService


class FakeDb:
    committed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: object) -> None:
        return None


class FakeSubscriptionsRepository:
    subscriptions: dict[uuid.UUID, Subscription] = {}

    def __init__(self, _: object) -> None:
        pass

    async def get_subscription(self, *, store_id: uuid.UUID) -> Subscription | None:
        return type(self).subscriptions.get(store_id)

    async def get_subscription_for_update(self, *, store_id: uuid.UUID) -> Subscription | None:
        return type(self).subscriptions.get(store_id)


@pytest.fixture(autouse=True)
def patch_repo(monkeypatch):
    from app.modules.subscriptions import service as subscriptions_service

    FakeSubscriptionsRepository.subscriptions = {}
    monkeypatch.setattr(
        subscriptions_service,
        "SubscriptionsRepository",
        FakeSubscriptionsRepository,
    )


def make_subscription(store_id: uuid.UUID) -> Subscription:
    subscription = Subscription(
        id=uuid.uuid4(),
        store_id=store_id,
        plan=SubscriptionPlan.FREE.value,
        status=SubscriptionStatus.TRIALING.value,
        starts_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC) + timedelta(days=1),
        max_products=100,
        max_users=2,
    )
    FakeSubscriptionsRepository.subscriptions[store_id] = subscription
    return subscription


@pytest.mark.asyncio
async def test_activate_subscription_sets_active_plan() -> None:
    store_id = uuid.uuid4()
    make_subscription(store_id)

    result = await SubscriptionsService(FakeDb()).activate(
        store_id=store_id,
        payload=SubscriptionActivateRequest(plan=SubscriptionPlan.PRO, months=2),
    )

    assert result.plan == SubscriptionPlan.PRO.value
    assert result.status == SubscriptionStatus.ACTIVE.value
    assert result.read_only is False
    assert result.expires_at is not None


@pytest.mark.asyncio
async def test_cancel_subscription_sets_cancelled() -> None:
    store_id = uuid.uuid4()
    make_subscription(store_id)

    result = await SubscriptionsService(FakeDb()).cancel(store_id=store_id)

    assert result.status == SubscriptionStatus.CANCELLED.value
    assert result.read_only is True


@pytest.mark.asyncio
async def test_update_subscription_limits() -> None:
    store_id = uuid.uuid4()
    make_subscription(store_id)

    result = await SubscriptionsService(FakeDb()).update(
        store_id=store_id,
        payload=SubscriptionUpdateRequest(max_products=500, max_users=10),
    )

    assert result.max_products == 500
    assert result.max_users == 10


@pytest.mark.asyncio
async def test_missing_subscription_raises() -> None:
    with pytest.raises(AppException) as exc:
        await SubscriptionsService(FakeDb()).get_current(store_id=uuid.uuid4())

    assert exc.value.code == "SUBSCRIPTION_NOT_FOUND"
