from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.core.deps import CsrfGuard, CurrentAuth, DbSession
from app.core.rate_limit import enforce_rate_limit, rate_limit
from app.core.responses import ApiResponse
from app.core.security import (
    ACCESS_TOKEN_COOKIE,
    CSRF_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    blacklist_token,
)
from app.modules.auth.otp import OtpService
from app.modules.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    PasswordResetRequest,
    RegisterRequest,
    SelectStoreRequest,
)
from app.modules.auth.service import AuthService
from app.utils.phone import normalize_phone

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_max_age() -> int:
    return int(timedelta(minutes=settings.access_token_expire_minutes).total_seconds())


def _refresh_cookie_max_age() -> int:
    return int(timedelta(days=settings.refresh_token_expire_days).total_seconds())


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    access_max_age = _cookie_max_age()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=access_max_age,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=_refresh_cookie_max_age(),
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=csrf_token,
        max_age=access_max_age,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=CSRF_TOKEN_COOKIE, path="/")


@router.post(
    "/otp/send",
    response_model=ApiResponse[OtpSendResponse],
    dependencies=[rate_limit(key_prefix="auth_otp_send", limit=5, window_seconds=60)],
)
async def send_otp(payload: OtpSendRequest) -> ApiResponse[OtpSendResponse]:
    await enforce_rate_limit(
        key_prefix="auth_otp_send_phone",
        key=normalize_phone(payload.phone),
        limit=3,
        window_seconds=300,
    )
    result = await OtpService().send_code(phone=payload.phone, purpose=payload.purpose)
    return ApiResponse(
        data=OtpSendResponse(
            phone=result.phone,
            expires_in=result.expires_in,
            resend_after=result.resend_after,
            debug_code=result.debug_code,
        ),
        message="Tasdiqlash kodi yuborildi.",
    )


@router.post(
    "/otp/verify",
    response_model=ApiResponse[OtpVerifyResponse],
    dependencies=[rate_limit(key_prefix="auth_otp_verify", limit=10, window_seconds=60)],
)
async def verify_otp(payload: OtpVerifyRequest) -> ApiResponse[OtpVerifyResponse]:
    await enforce_rate_limit(
        key_prefix="auth_otp_verify_phone",
        key=f"{payload.purpose.value}:{normalize_phone(payload.phone)}",
        limit=10,
        window_seconds=300,
    )
    result = await OtpService().verify_code(
        phone=payload.phone,
        purpose=payload.purpose,
        code=payload.code,
    )
    return ApiResponse(
        data=OtpVerifyResponse(
            phone=result.phone,
            verification_token=result.verification_token,
            expires_in=result.expires_in,
        ),
        message="Telefon raqam tasdiqlandi.",
    )


@router.post(
    "/register",
    response_model=ApiResponse[AuthResponse],
    dependencies=[rate_limit(key_prefix="auth_register", limit=5, window_seconds=60)],
)
async def register(
    payload: RegisterRequest,
    response: Response,
    db: DbSession,
) -> ApiResponse[AuthResponse]:
    await enforce_rate_limit(
        key_prefix="auth_register_phone",
        key=normalize_phone(payload.phone),
        limit=5,
        window_seconds=3600,
    )
    session = await AuthService(db).register(payload)
    set_auth_cookies(
        response,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        csrf_token=session.response.csrf_token,
    )
    return ApiResponse(data=session.response, message="Ro'yxatdan o'tish muvaffaqiyatli.")


@router.post(
    "/login",
    response_model=ApiResponse[AuthResponse],
    dependencies=[rate_limit(key_prefix="auth_login", limit=10, window_seconds=60)],
)
async def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
) -> ApiResponse[AuthResponse]:
    await enforce_rate_limit(
        key_prefix="auth_login_phone",
        key=normalize_phone(payload.phone),
        limit=10,
        window_seconds=300,
    )
    session = await AuthService(db).login(payload)
    set_auth_cookies(
        response,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        csrf_token=session.response.csrf_token,
    )
    return ApiResponse(data=session.response, message="Tizimga kirish muvaffaqiyatli.")


@router.post(
    "/password/reset",
    response_model=ApiResponse[dict[str, bool]],
    dependencies=[rate_limit(key_prefix="auth_password_reset", limit=5, window_seconds=60)],
)
async def reset_password(
    payload: PasswordResetRequest,
    db: DbSession,
) -> ApiResponse[dict[str, bool]]:
    await enforce_rate_limit(
        key_prefix="auth_password_reset_phone",
        key=normalize_phone(payload.phone),
        limit=5,
        window_seconds=3600,
    )
    await AuthService(db).reset_password(payload)
    return ApiResponse(data={"password_reset": True}, message="Parol yangilandi.")


@router.post(
    "/refresh",
    response_model=ApiResponse[AuthResponse],
    dependencies=[rate_limit(key_prefix="auth_refresh", limit=30, window_seconds=60)],
)
async def refresh(
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[AuthResponse]:
    session = await AuthService(db).refresh(request.cookies.get(REFRESH_TOKEN_COOKIE))
    set_auth_cookies(
        response,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        csrf_token=session.response.csrf_token,
    )
    return ApiResponse(data=session.response, message="Sessiya yangilandi.")


@router.post(
    "/select-store",
    response_model=ApiResponse[AuthResponse],
)
async def select_store(
    payload: SelectStoreRequest,
    response: Response,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
) -> ApiResponse[AuthResponse]:
    session = await AuthService(db).select_store(user_id=auth.user_id, store_id=payload.store_id)
    set_auth_cookies(
        response,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        csrf_token=session.response.csrf_token,
    )
    return ApiResponse(data=session.response, message="Do'kon tanlandi.")


@router.get("/me", response_model=ApiResponse[MeResponse])
async def me(db: DbSession, auth: CurrentAuth) -> ApiResponse[MeResponse]:
    data = await AuthService(db).me(user_id=auth.user_id, active_store_id=auth.store_id)
    return ApiResponse(data=data)


@router.post("/logout", response_model=ApiResponse[dict[str, bool]])
async def logout(
    request: Request,
    response: Response,
    auth: CurrentAuth,
    _: CsrfGuard,
) -> ApiResponse[dict[str, bool]]:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if auth.token_source == "bearer":
        authorization = request.headers.get("authorization", "")
        _, _, access_token = authorization.partition(" ")
    await blacklist_token(access_token or "")
    await blacklist_token(request.cookies.get(REFRESH_TOKEN_COOKIE) or "")
    clear_auth_cookies(response)
    return ApiResponse(data={"logged_out": True}, message="Tizimdan chiqildi.")
