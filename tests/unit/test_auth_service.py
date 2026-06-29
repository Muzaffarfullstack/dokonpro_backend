import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.constants import DEFAULT_MAX_PRODUCTS, DEFAULT_MAX_USERS, TRIAL_DAYS
from app.core.enums import OtpPurpose, SubscriptionPlan, SubscriptionStatus, UserRole
from app.core.exceptions import AppException
from app.core.security import decode_token, hash_password, verify_password
from app.models import Store, Subscription, User
from app.modules.auth.schemas import LoginRequest, PasswordResetRequest, RegisterRequest
from app.modules.auth.service import AuthService
from app.utils.phone import normalize_phone


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeAuthRepository:
    user: User | None = None
    existing_phone: User | None = None
    stores: list[Store] = []
    selected_store: Store | None = None
    created_subscription: Subscription | None = None

    def __init__(self, _: object) -> None:
        pass

    async def get_user_by_phone(self, _: str) -> User | None:
        return type(self).existing_phone or type(self).user

    async def get_user_by_id(self, _: uuid.UUID) -> User | None:
        return type(self).user

    async def create_user(self, *, full_name: str, phone: str, password_hash: str) -> User:
        type(self).user = User(
            id=uuid.uuid4(),
            full_name=full_name,
            phone=phone,
            password_hash=password_hash,
            role=UserRole.OWNER.value,
            is_active=True,
        )
        return type(self).user

    async def update_password(self, *, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        return user

    async def create_store(self, *, owner_id: uuid.UUID, name: str, slug: str) -> Store:
        store = Store(
            id=uuid.uuid4(),
            owner_id=owner_id,
            name=name,
            slug=slug,
            is_active=True,
        )
        type(self).stores = [store]
        return store

    async def create_subscription(
        self,
        *,
        store_id: uuid.UUID,
        starts_at: datetime,
        trial_ends_at: datetime,
    ) -> Subscription:
        subscription = Subscription(
            id=uuid.uuid4(),
            store_id=store_id,
            plan=SubscriptionPlan.FREE.value,
            status=SubscriptionStatus.TRIALING.value,
            starts_at=starts_at,
            trial_ends_at=trial_ends_at,
            max_products=DEFAULT_MAX_PRODUCTS,
            max_users=DEFAULT_MAX_USERS,
        )
        type(self).created_subscription = subscription
        type(self).stores[0].subscription = subscription
        return subscription

    async def list_user_stores(self, _: uuid.UUID) -> list[Store]:
        return type(self).stores

    async def get_user_store(self, *, user_id: uuid.UUID, store_id: uuid.UUID) -> Store | None:
        return type(self).selected_store


class FakeOtpService:
    consumed_codes: list[tuple[str, OtpPurpose, str]] = []
    consumed_tokens: list[tuple[str, OtpPurpose, str]] = []
    normalized_phone = "+998901234567"

    async def consume_code(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        code: str,
    ) -> str:
        type(self).consumed_codes.append((phone, purpose, code))
        return type(self).normalized_phone

    async def consume_verification(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        verification_token: str,
    ) -> str:
        type(self).consumed_tokens.append((phone, purpose, verification_token))
        return type(self).normalized_phone


@pytest.fixture(autouse=True)
def reset_fake_repo(monkeypatch):
    from app.modules.auth import service as auth_service

    FakeAuthRepository.user = None
    FakeAuthRepository.existing_phone = None
    FakeAuthRepository.stores = []
    FakeAuthRepository.selected_store = None
    FakeAuthRepository.created_subscription = None
    FakeOtpService.consumed_codes = []
    FakeOtpService.consumed_tokens = []
    FakeOtpService.normalized_phone = "+998901234567"
    monkeypatch.setattr(auth_service, "AuthRepository", FakeAuthRepository)


def make_user(*, active: bool = True, password: str = "secret123") -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Ali Valiyev",
        phone="+998901234567",
        password_hash=hash_password(password),
        role=UserRole.OWNER.value,
        is_active=active,
    )


def make_store(*, name: str = "Asaka Savdo Markazi", expired: bool = False) -> Store:
    store = Store(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name=name,
        slug="asaka-savdo-markazi",
        is_active=True,
    )
    trial_ends_at = (
        datetime.now(UTC) - timedelta(days=1) if expired else datetime.now(UTC) + timedelta(days=7)
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


def test_normalize_phone_accepts_global_formats() -> None:
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"
    assert normalize_phone("+1 (555) 111-2233") == "+15551112233"
    assert normalize_phone("0044 20 7946 0958") == "+442079460958"
    assert normalize_phone("90 123 45 67") == "+998901234567"


def test_normalize_phone_rejects_invalid_number() -> None:
    with pytest.raises(AppException) as exc:
        normalize_phone("123")

    assert exc.value.code == "INVALID_PHONE"
    assert exc.value.field == "phone"


def test_register_schema_requires_password_confirmation_match() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            first_name="Ali",
            last_name="Valiyev",
            store_name="Asaka Savdo Markazi",
            phone="+998901234567",
            password="secret123",
            password_confirm="different123",
            otp_code="123456",
        )


@pytest.mark.asyncio
async def test_register_creates_user_store_and_seven_day_trial() -> None:
    db = FakeDb()
    session = await AuthService(db, otp_service=FakeOtpService()).register(
        RegisterRequest(
            first_name="Ali",
            last_name="Valiyev",
            store_name="Asaka Savdo Markazi",
            phone="+998 90 123 45 67",
            password="secret123",
            password_confirm="secret123",
            otp_code="123456",
        )
    )

    assert db.committed is True
    assert session.response.user.phone == "+998901234567"
    assert FakeOtpService.consumed_codes == [("+998901234567", OtpPurpose.REGISTER, "123456")]
    assert session.response.active_store is not None
    assert session.response.active_store.read_only is False
    assert session.response.active_store.subscription_status == SubscriptionStatus.TRIALING.value
    assert FakeAuthRepository.created_subscription is not None
    trial_delta = FakeAuthRepository.created_subscription.trial_ends_at - datetime.now(UTC)
    assert timedelta(days=TRIAL_DAYS - 1) < trial_delta <= timedelta(days=TRIAL_DAYS)

    token_payload = decode_token(session.access_token)
    refresh_payload = decode_token(session.refresh_token)
    assert token_payload is not None
    assert token_payload["sub"] == str(session.response.user.id)
    assert token_payload["store_id"] == str(session.response.active_store.id)
    assert token_payload["csrf"] == session.response.csrf_token
    assert refresh_payload is not None
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["sub"] == str(session.response.user.id)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_phone() -> None:
    FakeAuthRepository.existing_phone = make_user()

    with pytest.raises(AppException) as exc:
        await AuthService(FakeDb(), otp_service=FakeOtpService()).register(
            RegisterRequest(
                first_name="Ali",
                last_name="Valiyev",
                store_name="Asaka Savdo Markazi",
                phone="+998901234567",
                password="secret123",
                password_confirm="secret123",
                otp_code="123456",
            )
        )

    assert exc.value.code == "PHONE_ALREADY_EXISTS"
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_login_single_store_sets_active_store() -> None:
    user = make_user()
    store = make_store()
    FakeAuthRepository.user = user
    FakeAuthRepository.stores = [store]

    session = await AuthService(FakeDb()).login(
        LoginRequest(phone="+998 90 123 45 67", password="secret123")
    )

    assert session.response.requires_store_selection is False
    assert session.response.active_store is not None
    assert session.response.active_store.id == store.id


@pytest.mark.asyncio
async def test_login_multiple_stores_requires_store_selection() -> None:
    user = make_user()
    FakeAuthRepository.user = user
    FakeAuthRepository.stores = [make_store(name="Store A"), make_store(name="Store B")]

    session = await AuthService(FakeDb()).login(
        LoginRequest(phone="+998901234567", password="secret123")
    )

    assert session.response.requires_store_selection is True
    assert session.response.active_store is None
    assert len(session.response.stores) == 2
    assert "store_id" not in decode_token(session.access_token)
    assert decode_token(session.refresh_token)["type"] == "refresh"


@pytest.mark.asyncio
async def test_login_rejects_bad_password() -> None:
    FakeAuthRepository.user = make_user()

    with pytest.raises(AppException) as exc:
        await AuthService(FakeDb()).login(LoginRequest(phone="+998901234567", password="wrongpass"))

    assert exc.value.code == "INVALID_CREDENTIALS"
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_inactive_user() -> None:
    FakeAuthRepository.user = make_user(active=False)

    with pytest.raises(AppException) as exc:
        await AuthService(FakeDb()).login(LoginRequest(phone="+998901234567", password="secret123"))

    assert exc.value.code == "USER_INACTIVE"
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_reset_password_consumes_password_reset_token() -> None:
    user = make_user(password="oldsecret")
    FakeAuthRepository.user = user

    await AuthService(FakeDb(), otp_service=FakeOtpService()).reset_password(
        PasswordResetRequest(
            phone="+998 90 123 45 67",
            phone_verification_token="reset-token-123456",
            new_password="newsecret123",
            new_password_confirm="newsecret123",
        )
    )

    assert FakeOtpService.consumed_tokens == [
        ("+998901234567", OtpPurpose.PASSWORD_RESET, "reset-token-123456")
    ]
    assert verify_password("newsecret123", user.password_hash)


@pytest.mark.asyncio
async def test_select_store_issues_token_with_selected_store() -> None:
    user = make_user()
    selected_store = make_store()
    FakeAuthRepository.user = user
    FakeAuthRepository.selected_store = selected_store
    FakeAuthRepository.stores = [make_store(name="A"), selected_store]

    session = await AuthService(FakeDb()).select_store(
        user_id=user.id,
        store_id=selected_store.id,
    )

    assert session.response.active_store is not None
    assert session.response.active_store.id == selected_store.id
    assert decode_token(session.access_token)["store_id"] == str(selected_store.id)
    assert decode_token(session.refresh_token)["store_id"] == str(selected_store.id)


@pytest.mark.asyncio
async def test_refresh_rotates_session_with_selected_store(monkeypatch) -> None:
    async def fake_blacklist_token(_: str) -> None:
        return None

    async def fake_is_token_blacklisted(_: str | None) -> bool:
        return False

    from app.modules.auth import service as auth_service

    monkeypatch.setattr(auth_service, "blacklist_token", fake_blacklist_token)
    monkeypatch.setattr(auth_service, "is_token_blacklisted", fake_is_token_blacklisted)

    user = make_user()
    selected_store = make_store()
    FakeAuthRepository.user = user
    FakeAuthRepository.stores = [selected_store]

    initial_session = AuthService(FakeDb())._build_session(
        user=user,
        stores=[selected_store],
        active_store_id=selected_store.id,
    )
    refreshed_session = await AuthService(FakeDb()).refresh(initial_session.refresh_token)

    assert refreshed_session.response.active_store is not None
    assert refreshed_session.response.active_store.id == selected_store.id
    assert refreshed_session.refresh_token != initial_session.refresh_token


@pytest.mark.asyncio
async def test_me_marks_expired_trial_as_read_only() -> None:
    user = make_user()
    expired_store = make_store(expired=True)
    FakeAuthRepository.user = user
    FakeAuthRepository.stores = [expired_store]

    response = await AuthService(FakeDb()).me(user_id=user.id, active_store_id=expired_store.id)

    assert response.active_store is not None
    assert response.active_store.read_only is True
    assert response.active_store.subscription_status == SubscriptionStatus.EXPIRED.value
