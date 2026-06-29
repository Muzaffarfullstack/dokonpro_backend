from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import ActiveStoreId, CsrfGuard, DbSession, get_auth_context, require_roles
from app.core.enums import UserRole
from app.core.responses import ApiResponse
from app.modules.subscriptions.schemas import (
    SubscriptionActivateRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.modules.subscriptions.service import SubscriptionsService

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/current", response_model=ApiResponse[SubscriptionResponse])
async def get_current_subscription(
    db: DbSession,
    store_id: ActiveStoreId,
) -> ApiResponse[SubscriptionResponse]:
    subscription = await SubscriptionsService(db).get_current(store_id=store_id)
    return ApiResponse(data=subscription)


@router.post("/activate", response_model=ApiResponse[SubscriptionResponse])
async def activate_subscription(
    payload: SubscriptionActivateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[SubscriptionResponse]:
    subscription = await SubscriptionsService(db).activate(store_id=store_id, payload=payload)
    return ApiResponse(data=subscription, message="Tarif faollashtirildi.")


@router.post("/cancel", response_model=ApiResponse[SubscriptionResponse])
async def cancel_subscription(
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[SubscriptionResponse]:
    subscription = await SubscriptionsService(db).cancel(store_id=store_id)
    return ApiResponse(data=subscription, message="Tarif bekor qilindi.")


@router.patch("/current", response_model=ApiResponse[SubscriptionResponse])
async def update_subscription(
    payload: SubscriptionUpdateRequest,
    db: DbSession,
    store_id: ActiveStoreId,
    _: CsrfGuard,
    __: None = Depends(require_roles(UserRole.OWNER)),
) -> ApiResponse[SubscriptionResponse]:
    subscription = await SubscriptionsService(db).update(store_id=store_id, payload=payload)
    return ApiResponse(data=subscription, message="Tarif yangilandi.")
