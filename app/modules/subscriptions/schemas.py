from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SubscriptionPlan, SubscriptionStatus


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    plan: str
    status: str
    read_only: bool
    starts_at: datetime | None
    trial_ends_at: datetime | None
    expires_at: datetime | None
    max_products: int
    max_users: int


class SubscriptionActivateRequest(BaseModel):
    plan: SubscriptionPlan = SubscriptionPlan.PRO
    months: int = Field(default=1, ge=1, le=24)


class SubscriptionUpdateRequest(BaseModel):
    plan: SubscriptionPlan | None = None
    status: SubscriptionStatus | None = None
    trial_ends_at: datetime | None = None
    expires_at: datetime | None = None
    max_products: int | None = Field(default=None, ge=0)
    max_users: int | None = Field(default=None, ge=0)
