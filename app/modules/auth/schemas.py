from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import OtpPurpose


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=60)
    last_name: str = Field(min_length=2, max_length=60)
    store_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=9, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    otp_code: str = Field(min_length=4, max_length=8)

    @field_validator("first_name", "last_name", "store_name", "phone", "otp_code")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_password_match(self) -> RegisterRequest:
        if self.password != self.password_confirm:
            raise ValueError("Parol tasdiqlash mos kelmadi.")
        return self


class LoginRequest(BaseModel):
    phone: str = Field(min_length=9, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: str) -> str:
        return value.strip()


class SelectStoreRequest(BaseModel):
    store_id: uuid.UUID


class OtpSendRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=32)
    purpose: OtpPurpose

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: str) -> str:
        return value.strip()


class OtpSendResponse(BaseModel):
    phone: str
    expires_in: int
    resend_after: int
    debug_code: str | None = None


class OtpVerifyRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=32)
    purpose: OtpPurpose
    code: str = Field(min_length=4, max_length=8)

    @field_validator("phone", "code")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class OtpVerifyResponse(BaseModel):
    phone: str
    verification_token: str
    expires_in: int


class PasswordResetRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=32)
    phone_verification_token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirm: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def strip_phone(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_password_match(self) -> PasswordResetRequest:
        if self.new_password != self.new_password_confirm:
            raise ValueError("Parol tasdiqlash mos kelmadi.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    role: str


class AuthStoreResponse(BaseModel):
    id: uuid.UUID
    name: str
    read_only: bool
    subscription_status: str
    trial_ends_at: datetime | None = None


class AuthResponse(BaseModel):
    user: UserResponse
    stores: list[AuthStoreResponse]
    active_store: AuthStoreResponse | None = None
    requires_store_selection: bool
    csrf_token: str


class MeResponse(BaseModel):
    user: UserResponse
    stores: list[AuthStoreResponse]
    active_store: AuthStoreResponse | None = None
    requires_store_selection: bool
