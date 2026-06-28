from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TRIAL_DAYS
from app.core.enums import OtpPurpose, UserRole
from app.core.exceptions import AppException
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    hash_password,
    is_token_blacklisted,
    verify_password,
)
from app.models import Store, User
from app.modules.auth.otp import OtpService
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AuthResponse,
    AuthStoreResponse,
    LoginRequest,
    MeResponse,
    PasswordResetRequest,
    RegisterRequest,
    UserResponse,
)
from app.utils.phone import normalize_phone
from app.utils.slug import slugify
from app.utils.subscription import subscription_allows_write, subscription_status


@dataclass(frozen=True)
class AuthSession:
    response: AuthResponse
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: AsyncSession, otp_service: OtpService | None = None) -> None:
        self.db = db
        self.repo = AuthRepository(db)
        self.otp_service = otp_service

    async def register(self, payload: RegisterRequest) -> AuthSession:
        phone = normalize_phone(payload.phone)
        existing_user = await self.repo.get_user_by_phone(phone)
        if existing_user is not None:
            raise AppException(
                code="PHONE_ALREADY_EXISTS",
                message="Bu telefon raqam bilan hisob mavjud.",
                status_code=409,
                field="phone",
            )

        await self._otp_service().consume_code(
            phone=phone,
            purpose=OtpPurpose.REGISTER,
            code=payload.otp_code,
        )

        now = datetime.now(UTC)
        full_name = f"{payload.first_name} {payload.last_name}".strip()
        store_slug = slugify(payload.store_name) or "store"

        user = await self.repo.create_user(
            full_name=full_name,
            phone=phone,
            password_hash=hash_password(payload.password),
        )
        store = await self.repo.create_store(
            owner_id=user.id,
            name=payload.store_name,
            slug=store_slug,
        )
        await self.repo.create_subscription(
            store_id=store.id,
            starts_at=now,
            trial_ends_at=now + timedelta(days=TRIAL_DAYS),
        )
        await self.db.commit()

        stores = await self.repo.list_user_stores(user.id)
        return self._build_session(user=user, stores=stores, active_store_id=store.id)

    async def reset_password(self, payload: PasswordResetRequest) -> None:
        phone = normalize_phone(payload.phone)
        user = await self.repo.get_user_by_phone(phone)
        if user is None:
            raise AppException(
                code="USER_NOT_FOUND",
                message="Bu telefon raqam bilan hisob topilmadi.",
                status_code=404,
            )

        await self._otp_service().consume_verification(
            phone=phone,
            purpose=OtpPurpose.PASSWORD_RESET,
            verification_token=payload.phone_verification_token,
        )

        await self.repo.update_password(
            user=user,
            password_hash=hash_password(payload.new_password),
        )
        await self.db.commit()

    def _otp_service(self) -> OtpService:
        if self.otp_service is None:
            self.otp_service = OtpService()
        return self.otp_service

    async def login(self, payload: LoginRequest) -> AuthSession:
        phone = normalize_phone(payload.phone)
        user = await self.repo.get_user_by_phone(phone)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppException(
                code="INVALID_CREDENTIALS",
                message="Telefon raqam yoki parol noto'g'ri.",
                status_code=401,
            )

        if not user.is_active:
            raise AppException(
                code="USER_INACTIVE",
                message="Hisob bloklangan.",
                status_code=403,
            )

        stores = await self.repo.list_user_stores(user.id)
        active_store_id = stores[0].id if len(stores) == 1 else None
        return self._build_session(user=user, stores=stores, active_store_id=active_store_id)

    async def refresh(self, refresh_token: str | None) -> AuthSession:
        payload = decode_token(refresh_token or "")
        if (
            payload is None
            or payload.get("type") != "refresh"
            or not payload.get("sub")
            or await is_token_blacklisted(str(payload.get("jti") or ""))
        ):
            raise AppException(code="INVALID_TOKEN", message="Token noto'g'ri.", status_code=401)

        try:
            user_id = uuid.UUID(str(payload["sub"]))
            active_store_id = (
                uuid.UUID(str(payload["store_id"])) if payload.get("store_id") else None
            )
        except ValueError as exc:
            raise AppException(
                code="INVALID_TOKEN",
                message="Token noto'g'ri.",
                status_code=401,
            ) from exc

        user = await self.repo.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AppException(code="UNAUTHORIZED", message="Avtorizatsiya kerak.", status_code=401)

        stores = await self.repo.list_user_stores(user.id)
        if active_store_id is not None and all(store.id != active_store_id for store in stores):
            active_store_id = None
        if active_store_id is None and len(stores) == 1:
            active_store_id = stores[0].id

        await blacklist_token(refresh_token or "")
        return self._build_session(user=user, stores=stores, active_store_id=active_store_id)

    async def select_store(self, *, user_id: uuid.UUID, store_id: uuid.UUID) -> AuthSession:
        user = await self.repo.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AppException(code="UNAUTHORIZED", message="Avtorizatsiya kerak.", status_code=401)

        store = await self.repo.get_user_store(user_id=user.id, store_id=store_id)
        if store is None:
            raise AppException(
                code="STORE_NOT_FOUND",
                message="Do'kon topilmadi yoki sizga tegishli emas.",
                status_code=404,
            )

        stores = await self.repo.list_user_stores(user.id)
        return self._build_session(user=user, stores=stores, active_store_id=store.id)

    async def me(self, *, user_id: uuid.UUID, active_store_id: uuid.UUID | None) -> MeResponse:
        user = await self.repo.get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AppException(code="UNAUTHORIZED", message="Avtorizatsiya kerak.", status_code=401)

        stores = await self.repo.list_user_stores(user.id)
        store_responses = [self._store_response(store) for store in stores]
        active_store = next(
            (store for store in store_responses if store.id == active_store_id),
            None,
        )
        return MeResponse(
            user=UserResponse.model_validate(user),
            stores=store_responses,
            active_store=active_store,
            requires_store_selection=len(stores) > 1 and active_store is None,
        )

    def _build_session(
        self,
        *,
        user: User,
        stores: list[Store],
        active_store_id: uuid.UUID | None,
    ) -> AuthSession:
        csrf_token = generate_csrf_token()
        store_responses = [self._store_response(store) for store in stores]
        active_store = next(
            (store for store in store_responses if store.id == active_store_id),
            None,
        )
        token_claims: dict[str, str] = {
            "role": user.role or UserRole.OWNER.value,
            "csrf": csrf_token,
        }
        if active_store is not None:
            token_claims["store_id"] = str(active_store.id)

        refresh_claims = {key: value for key, value in token_claims.items() if key != "csrf"}
        access_token = create_access_token(str(user.id), token_claims)
        refresh_token = create_refresh_token(str(user.id), refresh_claims)
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            response=AuthResponse(
                user=UserResponse.model_validate(user),
                stores=store_responses,
                active_store=active_store,
                requires_store_selection=len(stores) > 1 and active_store is None,
                csrf_token=csrf_token,
            ),
        )

    def _store_response(self, store: Store) -> AuthStoreResponse:
        subscription = store.subscription
        return AuthStoreResponse(
            id=store.id,
            name=store.name,
            read_only=not subscription_allows_write(subscription),
            subscription_status=subscription_status(subscription),
            trial_ends_at=subscription.trial_ends_at if subscription else None,
        )
