import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.enums import PaymentMethod, PaymentStatus, SubscriptionPlan, SubscriptionStatus
from app.core.exceptions import AppException
from app.core.security import hash_password, verify_password
from app.models import Payment, Subscription, User
from app.modules.settings.schemas import (
    AccountSettingsUpdateRequest,
    PasswordChangeRequest,
)
from app.modules.settings.service import SettingsService


class FakeDb:
    committed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: object) -> None:
        return None


class FakeSettingsRepository:
    users: dict[uuid.UUID, User] = {}
    users_by_phone: dict[str, User] = {}
    subscriptions: dict[uuid.UUID, Subscription] = {}
    payments: dict[uuid.UUID, list[Payment]] = {}

    def __init__(self, _: object) -> None:
        pass

    async def get_user(self, *, user_id: uuid.UUID) -> User | None:
        return type(self).users.get(user_id)

    async def get_user_by_phone(self, *, phone: str) -> User | None:
        return type(self).users_by_phone.get(phone)

    async def get_subscription(self, *, store_id: uuid.UUID) -> Subscription | None:
        return type(self).subscriptions.get(store_id)

    async def list_store_payments(self, *, store_id: uuid.UUID) -> list[Payment]:
        return type(self).payments.get(store_id, [])


@pytest.fixture(autouse=True)
def patch_repo(monkeypatch):
    from app.modules.settings import service as settings_service

    FakeSettingsRepository.users = {}
    FakeSettingsRepository.users_by_phone = {}
    FakeSettingsRepository.subscriptions = {}
    FakeSettingsRepository.payments = {}
    monkeypatch.setattr(settings_service, "SettingsRepository", FakeSettingsRepository)


def make_user(*, phone: str = "+998901234567") -> User:
    user = User(
        id=uuid.uuid4(),
        full_name="Akmal Yuldashev",
        phone=phone,
        email="admin@dukonpro.uz",
        password_hash=hash_password("old-password"),
        is_active=True,
        is_verified=True,
    )
    FakeSettingsRepository.users[user.id] = user
    FakeSettingsRepository.users_by_phone[phone] = user
    return user


@pytest.mark.asyncio
async def test_update_account_settings() -> None:
    user = make_user()

    result = await SettingsService(FakeDb()).update_account_settings(
        user_id=user.id,
        payload=AccountSettingsUpdateRequest(
            first_name="Ali",
            last_name="Valiyev",
            email="ali@example.com",
            phone="+998901234568",
        ),
    )

    assert result.first_name == "Ali"
    assert user.full_name == "Ali Valiyev"
    assert user.phone == "+998901234568"


@pytest.mark.asyncio
async def test_update_account_rejects_duplicate_phone() -> None:
    user = make_user(phone="+998901234567")
    other = make_user(phone="+998901234568")

    with pytest.raises(AppException) as exc:
        await SettingsService(FakeDb()).update_account_settings(
            user_id=user.id,
            payload=AccountSettingsUpdateRequest(
                first_name="Ali",
                last_name="Valiyev",
                phone=other.phone,
            ),
        )

    assert exc.value.code == "PHONE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_change_password_verifies_current_password() -> None:
    user = make_user()

    await SettingsService(FakeDb()).change_password(
        user_id=user.id,
        payload=PasswordChangeRequest(
            current_password="old-password",
            new_password="new-password",
            new_password_confirm="new-password",
        ),
    )

    assert verify_password("new-password", user.password_hash)


@pytest.mark.asyncio
async def test_billing_settings_returns_subscription_and_payment_history() -> None:
    store_id = uuid.uuid4()
    FakeSettingsRepository.subscriptions[store_id] = Subscription(
        id=uuid.uuid4(),
        store_id=store_id,
        plan=SubscriptionPlan.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        max_products=100,
        max_users=2,
    )
    FakeSettingsRepository.payments[store_id] = [
        Payment(
            id=uuid.uuid4(),
            store_id=store_id,
            amount=Decimal("149000"),
            method=PaymentMethod.CASH.value,
            status=PaymentStatus.COMPLETED.value,
            paid_at=datetime.now(UTC),
        )
    ]

    result = await SettingsService(FakeDb()).get_billing_settings(store_id=store_id)

    assert result.subscription is not None
    assert result.subscription.plan == SubscriptionPlan.PRO.value
    assert result.payment_history[0].amount == Decimal("149000")
