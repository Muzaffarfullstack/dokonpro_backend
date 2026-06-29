from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.enums import UserRole
from app.core.exceptions import AppException
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    CSRF_HEADER,
    CSRF_TOKEN_COOKIE,
    decode_token,
    is_token_blacklisted,
)
from app.models import Store, User
from app.utils.subscription import subscription_allows_write

DbSession = Annotated[AsyncSession, Depends(get_db)]


@dataclass(frozen=True)
class AuthContext:
    user_id: uuid.UUID
    role: str
    csrf_token: str | None = None
    store_id: uuid.UUID | None = None
    token_id: str | None = None
    token_source: str = "cookie"


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _auth_token(request: Request) -> tuple[str | None, str]:
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if cookie_token:
        return cookie_token, "cookie"
    return _bearer_token(request), "bearer"


async def get_auth_context(request: Request) -> AuthContext:
    token, token_source = _auth_token(request)
    if not token:
        raise AppException(code="UNAUTHORIZED", message="Avtorizatsiya kerak.", status_code=401)

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access" or not payload.get("sub"):
        raise AppException(code="INVALID_TOKEN", message="Token noto'g'ri.", status_code=401)

    token_id = str(payload.get("jti") or "")
    if await is_token_blacklisted(token_id):
        raise AppException(code="TOKEN_REVOKED", message="Token bekor qilingan.", status_code=401)

    try:
        user_id = uuid.UUID(str(payload["sub"]))
        store_id = uuid.UUID(str(payload["store_id"])) if payload.get("store_id") else None
    except ValueError as exc:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token noto'g'ri.",
            status_code=401,
        ) from exc

    return AuthContext(
        user_id=user_id,
        role=str(payload.get("role") or UserRole.OWNER.value),
        csrf_token=payload.get("csrf"),
        store_id=store_id,
        token_id=token_id or None,
        token_source=token_source,
    )


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


async def get_current_user(db: DbSession, auth: CurrentAuth) -> User:
    result = await db.execute(select(User).where(User.id == auth.user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppException(code="UNAUTHORIZED", message="Avtorizatsiya kerak.", status_code=401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_csrf(
    request: Request,
    auth: CurrentAuth,
    csrf_header_token: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return

    if getattr(auth, "token_source", "cookie") == "bearer":
        return

    header_token = csrf_header_token or request.headers.get(CSRF_HEADER)
    if not header_token:
        raise AppException(
            code="CSRF_TOKEN_INVALID",
            message="CSRF token noto'g'ri.",
            status_code=403,
        )

    if auth.csrf_token:
        if header_token != auth.csrf_token:
            raise AppException(
                code="CSRF_TOKEN_INVALID",
                message="CSRF token noto'g'ri.",
                status_code=403,
            )
        return

    cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    if not cookie_token or header_token != cookie_token:
        raise AppException(
            code="CSRF_TOKEN_INVALID",
            message="CSRF token noto'g'ri.",
            status_code=403,
        )


CsrfGuard = Annotated[None, Depends(require_csrf)]


async def require_active_store(auth: CurrentAuth) -> uuid.UUID:
    if auth.store_id is None:
        raise AppException(
            code="STORE_SELECTION_REQUIRED",
            message="Avval do'konni tanlang.",
            status_code=409,
        )
    return auth.store_id


ActiveStoreId = Annotated[uuid.UUID, Depends(require_active_store)]


async def require_write_access(db: DbSession, store_id: ActiveStoreId) -> None:
    result = await db.execute(
        select(Store)
        .options(selectinload(Store.subscription))
        .where(Store.id == store_id, Store.is_active.is_(True))
    )
    store = result.scalar_one_or_none()
    if store is None:
        raise AppException(code="STORE_NOT_FOUND", message="Do'kon topilmadi.", status_code=404)

    if not subscription_allows_write(store.subscription):
        raise AppException(
            code="READ_ONLY_MODE",
            message="Trial muddati tugagan. Yozish amallari uchun to'lov qiling.",
            status_code=402,
        )


WriteAccess = Annotated[None, Depends(require_write_access)]


def require_roles(*allowed_roles: UserRole | str) -> Callable[[CurrentAuth], None]:
    allowed = {str(role.value if isinstance(role, UserRole) else role) for role in allowed_roles}

    async def dependency(auth: CurrentAuth) -> None:
        if auth.role not in allowed:
            raise AppException(
                code="FORBIDDEN_ROLE",
                message="Bu amal uchun ruxsat yo'q.",
                status_code=403,
            )

    return dependency


def role_values(roles: Iterable[UserRole]) -> tuple[str, ...]:
    return tuple(role.value for role in roles)
