import uuid
from datetime import UTC, datetime, timedelta

import pytest
from starlette.requests import Request

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS
from app.core.deps import (
    get_auth_context,
    require_active_store,
    require_csrf,
    require_roles,
    require_write_access,
)
from app.core.enums import SubscriptionPlan, SubscriptionStatus, UserRole
from app.core.exceptions import AppException
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    CSRF_HEADER,
    CSRF_TOKEN_COOKIE,
    create_access_token,
)
from app.models import Store, Subscription


def make_request(
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/",
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
        }
    )


class FakeScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class FakeDb:
    def __init__(self, store: Store | None) -> None:
        self.store = store

    async def execute(self, _: object) -> FakeScalarResult:
        return FakeScalarResult(self.store)


@pytest.mark.asyncio
async def test_get_auth_context_reads_httponly_cookie_token() -> None:
    user_id = uuid.uuid4()
    store_id = uuid.uuid4()
    token = create_access_token(
        str(user_id),
        {"role": UserRole.OWNER.value, "store_id": str(store_id), "csrf": "csrf-token"},
    )
    request = make_request(headers={"cookie": f"{ACCESS_TOKEN_COOKIE}={token}"})

    context = await get_auth_context(request)

    assert context.user_id == user_id
    assert context.store_id == store_id
    assert context.csrf_token == "csrf-token"
    assert context.token_id
    assert context.token_source == "cookie"


@pytest.mark.asyncio
async def test_get_auth_context_reads_bearer_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), {"role": UserRole.OWNER.value})
    request = make_request(headers={"authorization": f"Bearer {token}"})

    context = await get_auth_context(request)

    assert context.user_id == user_id
    assert context.token_source == "bearer"


@pytest.mark.asyncio
async def test_get_auth_context_rejects_missing_token() -> None:
    with pytest.raises(AppException) as exc:
        await get_auth_context(make_request())

    assert exc.value.code == "UNAUTHORIZED"
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_csrf_allows_matching_cookie_header_and_claim() -> None:
    token = "csrf-token"
    request = make_request(
        method="POST",
        headers={
            "cookie": f"{CSRF_TOKEN_COOKIE}={token}",
            CSRF_HEADER: token,
        },
    )

    await require_csrf(request, auth=type("Auth", (), {"csrf_token": token})())


@pytest.mark.asyncio
async def test_require_csrf_allows_matching_claim_without_csrf_cookie() -> None:
    token = "csrf-token"
    request = make_request(method="POST", headers={CSRF_HEADER: token})

    await require_csrf(request, auth=type("Auth", (), {"csrf_token": token})())


@pytest.mark.asyncio
async def test_require_csrf_rejects_missing_header() -> None:
    request = make_request(
        method="POST",
        headers={"cookie": f"{CSRF_TOKEN_COOKIE}=csrf-token"},
    )

    with pytest.raises(AppException) as exc:
        await require_csrf(request, auth=type("Auth", (), {"csrf_token": "csrf-token"})())

    assert exc.value.code == "CSRF_TOKEN_INVALID"
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_csrf_rejects_mismatched_claim() -> None:
    request = make_request(
        method="POST",
        headers={
            "cookie": f"{CSRF_TOKEN_COOKIE}=csrf-token",
            CSRF_HEADER: "csrf-token",
        },
    )

    with pytest.raises(AppException) as exc:
        await require_csrf(request, auth=type("Auth", (), {"csrf_token": "other-token"})())

    assert exc.value.code == "CSRF_TOKEN_INVALID"
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_csrf_skips_bearer_token_requests() -> None:
    request = make_request(method="POST")

    await require_csrf(
        request,
        auth=type("Auth", (), {"csrf_token": None, "token_source": "bearer"})(),
    )


@pytest.mark.asyncio
async def test_require_active_store_requires_selected_store() -> None:
    with pytest.raises(AppException) as exc:
        await require_active_store(type("Auth", (), {"store_id": None})())

    assert exc.value.code == "STORE_SELECTION_REQUIRED"
    assert exc.value.status_code == 409


def make_store(*, expired: bool) -> Store:
    store = Store(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="Asaka Savdo Markazi",
        slug="asaka-savdo-markazi",
        is_active=True,
    )
    trial_ends_at = (
        datetime.now(UTC) - timedelta(days=1) if expired else datetime.now(UTC) + timedelta(days=1)
    )
    store.subscription = Subscription(
        id=uuid.uuid4(),
        store_id=store.id,
        plan=SubscriptionPlan.FREE.value,
        status=SubscriptionStatus.TRIALING.value,
        starts_at=datetime.now(UTC),
        trial_ends_at=trial_ends_at,
        max_products=DEFAULT_MAX_PRODUCTS,
        max_users=DEFAULT_MAX_USERS,
    )
    return store


@pytest.mark.asyncio
async def test_require_write_access_allows_active_trial() -> None:
    await require_write_access(FakeDb(make_store(expired=False)), uuid.uuid4())


@pytest.mark.asyncio
async def test_require_write_access_blocks_expired_trial() -> None:
    with pytest.raises(AppException) as exc:
        await require_write_access(FakeDb(make_store(expired=True)), uuid.uuid4())

    assert exc.value.code == "READ_ONLY_MODE"
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_require_roles_allows_expected_role() -> None:
    dependency = require_roles(UserRole.OWNER, UserRole.MANAGER)

    await dependency(type("Auth", (), {"role": UserRole.OWNER.value})())


@pytest.mark.asyncio
async def test_require_roles_rejects_unexpected_role() -> None:
    dependency = require_roles(UserRole.OWNER, UserRole.MANAGER)

    with pytest.raises(AppException) as exc:
        await dependency(type("Auth", (), {"role": UserRole.CASHIER.value})())

    assert exc.value.code == "FORBIDDEN_ROLE"
    assert exc.value.status_code == 403
