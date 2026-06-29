import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.enums import SubscriptionPlan, SubscriptionStatus
from app.core.exceptions import AppException
from app.models import Store, Subscription
from app.modules.stores.schemas import StoreCreateRequest, StoreUpdateRequest
from app.modules.stores.service import StoresService


class FakeDb:
    committed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: object, attribute_names: list[str] | None = None) -> None:
        return None


class FakeStoresRepository:
    stores: dict[tuple[uuid.UUID, uuid.UUID], Store] = {}
    subscriptions: dict[uuid.UUID, Subscription] = {}

    def __init__(self, _: object) -> None:
        pass

    async def get_store(self, *, owner_id: uuid.UUID, store_id: uuid.UUID) -> Store | None:
        return type(self).stores.get((owner_id, store_id))

    async def get_store_by_slug(self, *, owner_id: uuid.UUID, slug: str) -> Store | None:
        for (current_owner_id, _), store in type(self).stores.items():
            if current_owner_id == owner_id and store.slug == slug and store.is_active:
                return store
        return None

    async def list_stores(self, *, owner_id: uuid.UUID) -> list[Store]:
        return [
            store
            for (current_owner_id, _), store in type(self).stores.items()
            if current_owner_id == owner_id and store.is_active
        ]

    async def count_stores(self, *, owner_id: uuid.UUID) -> int:
        return len(await self.list_stores(owner_id=owner_id))

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
            id=uuid.uuid4(),
            owner_id=owner_id,
            name=name,
            slug=slug,
            phone=phone,
            address=address,
            currency=currency,
            timezone=timezone,
            is_active=True,
        )
        type(self).stores[(owner_id, store.id)] = store
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
            id=uuid.uuid4(),
            store_id=store_id,
            plan=plan,
            status=status,
            starts_at=starts_at,
            trial_ends_at=trial_ends_at,
            max_products=max_products,
            max_users=max_users,
        )
        type(self).subscriptions[store_id] = subscription
        return subscription


@pytest.fixture(autouse=True)
def patch_repo(monkeypatch):
    from app.modules.stores import service as stores_service

    FakeStoresRepository.stores = {}
    FakeStoresRepository.subscriptions = {}
    monkeypatch.setattr(stores_service, "StoresRepository", FakeStoresRepository)


def make_store(owner_id: uuid.UUID, *, name: str = "Dukon") -> Store:
    store = Store(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=name,
        slug=name.lower(),
        currency="UZS",
        timezone="Asia/Tashkent",
        is_active=True,
    )
    store.subscription = Subscription(
        id=uuid.uuid4(),
        store_id=store.id,
        plan=SubscriptionPlan.FREE.value,
        status=SubscriptionStatus.TRIALING.value,
        starts_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC) + timedelta(days=1),
        max_products=100,
        max_users=2,
    )
    FakeStoresRepository.stores[(owner_id, store.id)] = store
    return store


@pytest.mark.asyncio
async def test_create_store_creates_trial_subscription() -> None:
    owner_id = uuid.uuid4()

    store = await StoresService(FakeDb()).create_store(
        owner_id=owner_id,
        payload=StoreCreateRequest(name="Dukon 2", currency="uzs"),
    )

    assert store.name == "Dukon 2"
    assert store.currency == "UZS"
    assert store.subscription is not None
    assert store.subscription.status == SubscriptionStatus.TRIALING.value


@pytest.mark.asyncio
async def test_create_store_rejects_duplicate_slug() -> None:
    owner_id = uuid.uuid4()
    make_store(owner_id, name="Dukon")

    with pytest.raises(AppException) as exc:
        await StoresService(FakeDb()).create_store(
            owner_id=owner_id,
            payload=StoreCreateRequest(name="Dukon"),
        )

    assert exc.value.code == "STORE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_and_delete_store() -> None:
    owner_id = uuid.uuid4()
    first = make_store(owner_id, name="Birinchi")
    second = make_store(owner_id, name="Ikkinchi")
    service = StoresService(FakeDb())

    updated = await service.update_store(
        owner_id=owner_id,
        store_id=first.id,
        payload=StoreUpdateRequest(name="Yangi nom"),
    )
    await service.deactivate_store(owner_id=owner_id, store_id=second.id)

    assert updated.slug == "yangi-nom"
    assert second.is_active is False
