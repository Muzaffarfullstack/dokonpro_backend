from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import (
    ActiveStoreId,
    CsrfGuard,
    CurrentAuth,
    DbSession,
    WriteAccess,
    get_auth_context,
    require_roles,
)
from app.core.enums import UserRole
from app.core.responses import ApiResponse
from app.modules.settings.schemas import (
    AccountSettingsResponse,
    AccountSettingsUpdateRequest,
    BillingSettingsResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    PasswordChangeRequest,
    SecuritySettingsResponse,
    StoreSettingsResponse,
    StoreSettingsUpdateRequest,
)
from app.modules.settings.service import SettingsService

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/store", response_model=ApiResponse[StoreSettingsResponse])
async def get_store_settings(
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[StoreSettingsResponse]:
    store = await SettingsService(db).get_store_settings(store_id=store_id)
    return ApiResponse(data=StoreSettingsResponse.model_validate(store))


@router.patch("/store", response_model=ApiResponse[StoreSettingsResponse])
async def update_store_settings(
    payload: StoreSettingsUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: WriteAccess,
    ___: None = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
) -> ApiResponse[StoreSettingsResponse]:
    store = await SettingsService(db).update_store_settings(store_id=store_id, payload=payload)
    return ApiResponse(
        data=StoreSettingsResponse.model_validate(store),
        message="Sozlamalar saqlandi.",
    )


@router.get("/account", response_model=ApiResponse[AccountSettingsResponse])
async def get_account_settings(
    db: DbSession,
    auth: CurrentAuth,
) -> ApiResponse[AccountSettingsResponse]:
    account = await SettingsService(db).get_account_settings(user_id=auth.user_id)
    return ApiResponse(data=account)


@router.patch("/account", response_model=ApiResponse[AccountSettingsResponse])
async def update_account_settings(
    payload: AccountSettingsUpdateRequest,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
) -> ApiResponse[AccountSettingsResponse]:
    account = await SettingsService(db).update_account_settings(
        user_id=auth.user_id,
        payload=payload,
    )
    return ApiResponse(data=account, message="Account ma'lumotlari saqlandi.")


@router.get("/security", response_model=ApiResponse[SecuritySettingsResponse])
async def get_security_settings(db: DbSession) -> ApiResponse[SecuritySettingsResponse]:
    return ApiResponse(data=await SettingsService(db).get_security_settings())


@router.post("/security/password", response_model=ApiResponse[dict[str, bool]])
async def change_password(
    payload: PasswordChangeRequest,
    db: DbSession,
    auth: CurrentAuth,
    _: CsrfGuard,
) -> ApiResponse[dict[str, bool]]:
    await SettingsService(db).change_password(user_id=auth.user_id, payload=payload)
    return ApiResponse(data={"changed": True}, message="Parol yangilandi.")


@router.get("/billing", response_model=ApiResponse[BillingSettingsResponse])
async def get_billing_settings(
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[BillingSettingsResponse]:
    billing = await SettingsService(db).get_billing_settings(store_id=store_id)
    return ApiResponse(data=billing)


@router.get("/notifications", response_model=ApiResponse[NotificationSettingsResponse])
async def get_notification_settings(
    db: DbSession,
) -> ApiResponse[NotificationSettingsResponse]:
    return ApiResponse(data=await SettingsService(db).get_notification_settings())


@router.patch("/notifications", response_model=ApiResponse[NotificationSettingsResponse])
async def update_notification_settings(
    payload: NotificationSettingsUpdateRequest,
    db: DbSession,
    _: CsrfGuard,
) -> ApiResponse[NotificationSettingsResponse]:
    settings = await SettingsService(db).update_notification_settings(payload)
    return ApiResponse(data=settings, message="Bildirishnoma sozlamalari saqlandi.")
