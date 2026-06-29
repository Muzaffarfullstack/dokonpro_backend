from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoreSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str | None
    address: str | None
    currency: str
    timezone: str


class StoreSettingsUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("name", "phone", "address", "currency", "timezone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class AccountSettingsResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str
    language: str = "uz"


class AccountSettingsUpdateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str | None = Field(default=None, max_length=255)
    phone: str = Field(min_length=8, max_length=32)
    language: str = Field(default="uz", min_length=2, max_length=12)

    @field_validator("first_name", "last_name", "email", "phone", "language")
    @classmethod
    def strip_account_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirm: str = Field(min_length=8, max_length=128)


class SecuritySettingsResponse(BaseModel):
    two_factor_enabled: bool = False


class NotificationSettingsResponse(BaseModel):
    low_stock_enabled: bool = True
    payment_enabled: bool = True
    trial_enabled: bool = True


class NotificationSettingsUpdateRequest(BaseModel):
    low_stock_enabled: bool = True
    payment_enabled: bool = True
    trial_enabled: bool = True


class BillingPaymentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    method: str
    status: str
    reference: str | None
    paid_at: datetime


class BillingSubscriptionResponse(BaseModel):
    plan: str
    status: str
    read_only: bool
    starts_at: datetime | None
    trial_ends_at: datetime | None
    expires_at: datetime | None
    max_products: int
    max_users: int


class BillingSettingsResponse(BaseModel):
    subscription: BillingSubscriptionResponse | None
    payment_history: list[BillingPaymentHistoryItem]
