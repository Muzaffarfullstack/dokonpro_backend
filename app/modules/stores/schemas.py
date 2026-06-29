from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoreCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    timezone: str = Field(default="Asia/Tashkent", min_length=1, max_length=64)

    @field_validator("name", "phone", "address", "currency", "timezone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class StoreUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("name", "phone", "address", "currency", "timezone")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class StoreSubscriptionSummary(BaseModel):
    plan: str
    status: str
    read_only: bool
    trial_ends_at: datetime | None
    expires_at: datetime | None


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    slug: str
    phone: str | None
    address: str | None
    currency: str
    timezone: str
    is_active: bool
    subscription: StoreSubscriptionSummary | None = None
