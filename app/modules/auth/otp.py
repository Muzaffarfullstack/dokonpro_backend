from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from hashlib import sha256

from app.core.config import settings
from app.core.database import get_redis
from app.core.enums import OtpPurpose
from app.core.exceptions import AppException
from app.integrations.sms import SmsProvider, get_sms_provider
from app.utils.phone import normalize_phone


@dataclass(frozen=True)
class OtpSendResult:
    phone: str
    expires_in: int
    resend_after: int
    debug_code: str | None = None


@dataclass(frozen=True)
class OtpVerifyResult:
    phone: str
    verification_token: str
    expires_in: int


class OtpService:
    def __init__(self, provider: SmsProvider | None = None) -> None:
        self.provider = provider or get_sms_provider()
        self.redis = get_redis()

    async def send_code(self, *, phone: str, purpose: OtpPurpose) -> OtpSendResult:
        normalized_phone = normalize_phone(phone)
        cooldown_key = self._cooldown_key(purpose, normalized_phone)

        if await self.redis.exists(cooldown_key):
            ttl = await self.redis.ttl(cooldown_key)
            raise AppException(
                code="OTP_RESEND_COOLDOWN",
                message="Kodni qayta yuborishdan oldin biroz kuting.",
                status_code=429,
                details={"retry_after": max(ttl, 1)},
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        await self.redis.setex(
            self._code_key(purpose, normalized_phone),
            settings.otp_code_ttl_seconds,
            self._hash_code(phone=normalized_phone, purpose=purpose, code=code),
        )
        await self.redis.setex(
            self._attempts_key(purpose, normalized_phone),
            settings.otp_code_ttl_seconds,
            "0",
        )
        await self.redis.setex(cooldown_key, settings.otp_resend_cooldown_seconds, "1")

        await self.provider.send_sms(
            phone=normalized_phone,
            message=f"DukonPro tasdiqlash kodi: {code}",
        )

        return OtpSendResult(
            phone=normalized_phone,
            expires_in=settings.otp_code_ttl_seconds,
            resend_after=settings.otp_resend_cooldown_seconds,
            debug_code=(
                code if settings.sms_provider == "fake" and not settings.is_production else None
            ),
        )

    async def verify_code(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        code: str,
    ) -> OtpVerifyResult:
        normalized_phone = await self._verify_code_hash(phone=phone, purpose=purpose, code=code)
        verification_token = secrets.token_urlsafe(32)
        await self.redis.setex(
            self._verified_key(purpose, normalized_phone, verification_token),
            settings.otp_verification_token_ttl_seconds,
            "1",
        )
        await self._clear_code(purpose, normalized_phone)

        return OtpVerifyResult(
            phone=normalized_phone,
            verification_token=verification_token,
            expires_in=settings.otp_verification_token_ttl_seconds,
        )

    async def consume_code(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        code: str,
    ) -> str:
        normalized_phone = await self._verify_code_hash(phone=phone, purpose=purpose, code=code)
        await self._clear_code(purpose, normalized_phone)
        return normalized_phone

    async def _verify_code_hash(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        code: str,
    ) -> str:
        normalized_phone = normalize_phone(phone)
        code_key = self._code_key(purpose, normalized_phone)
        expected_hash = await self.redis.get(code_key)
        if not expected_hash:
            raise AppException(
                code="OTP_EXPIRED",
                message="Tasdiqlash kodi eskirgan yoki topilmadi.",
                status_code=400,
            )

        attempts = await self.redis.incr(self._attempts_key(purpose, normalized_phone))
        if attempts > settings.otp_max_attempts:
            await self._clear_code(purpose, normalized_phone)
            raise AppException(
                code="OTP_TOO_MANY_ATTEMPTS",
                message="Kod juda ko'p marta noto'g'ri kiritildi.",
                status_code=429,
            )

        submitted_hash = self._hash_code(phone=normalized_phone, purpose=purpose, code=code)
        if not hmac.compare_digest(str(expected_hash), submitted_hash):
            raise AppException(
                code="OTP_INVALID",
                message="Tasdiqlash kodi noto'g'ri.",
                status_code=400,
            )

        return normalized_phone

    async def consume_verification(
        self,
        *,
        phone: str,
        purpose: OtpPurpose,
        verification_token: str,
    ) -> str:
        normalized_phone = normalize_phone(phone)
        key = self._verified_key(purpose, normalized_phone, verification_token)
        deleted_count = await self.redis.delete(key)
        if deleted_count == 0:
            raise AppException(
                code="PHONE_NOT_VERIFIED",
                message="Telefon raqam tasdiqlanmagan yoki token eskirgan.",
                status_code=400,
                field="phone_verification_token",
            )
        return normalized_phone

    async def _clear_code(self, purpose: OtpPurpose, phone: str) -> None:
        await self.redis.delete(
            self._code_key(purpose, phone),
            self._attempts_key(purpose, phone),
        )

    def _hash_code(self, *, phone: str, purpose: OtpPurpose, code: str) -> str:
        message = f"{purpose.value}:{phone}:{code}".encode()
        return hmac.new(settings.secret_key.encode(), message, sha256).hexdigest()

    def _code_key(self, purpose: OtpPurpose, phone: str) -> str:
        return f"otp:{purpose.value}:{phone}:code"

    def _attempts_key(self, purpose: OtpPurpose, phone: str) -> str:
        return f"otp:{purpose.value}:{phone}:attempts"

    def _cooldown_key(self, purpose: OtpPurpose, phone: str) -> str:
        return f"otp:{purpose.value}:{phone}:cooldown"

    def _verified_key(self, purpose: OtpPurpose, phone: str, token: str) -> str:
        return f"otp:{purpose.value}:{phone}:verified:{token}"
