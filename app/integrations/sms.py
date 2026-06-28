from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.core.database import get_redis
from app.core.enums import SmsProviderType
from app.core.exceptions import AppException

ESKIZ_TOKEN_CACHE_KEY = "sms:eskiz:token"
ESKIZ_TOKEN_TTL_SECONDS = 23 * 60 * 60


class SmsProvider(ABC):
    @abstractmethod
    async def send_sms(self, *, phone: str, message: str) -> None:
        raise NotImplementedError


class FakeSmsProvider(SmsProvider):
    async def send_sms(self, *, phone: str, message: str) -> None:
        return None


class EskizSmsProvider(SmsProvider):
    async def send_sms(self, *, phone: str, message: str) -> None:
        if not settings.eskiz_email or not settings.eskiz_password:
            raise AppException(
                code="SMS_PROVIDER_NOT_CONFIGURED",
                message="Eskiz SMS sozlamalari to'liq emas.",
                status_code=500,
            )

        async with httpx.AsyncClient(base_url=settings.eskiz_base_url, timeout=15) as client:
            token = await self._get_token(client)
            response = await client.post(
                "/message/sms/send",
                data={
                    "mobile_phone": phone.lstrip("+"),
                    "message": message,
                    "from": settings.eskiz_from,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code >= 400:
                raise AppException(
                    code="SMS_SEND_FAILED",
                    message="SMS kod yuborilmadi. Keyinroq qayta urinib ko'ring.",
                    status_code=502,
                )

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        try:
            cached_token = await get_redis().get(ESKIZ_TOKEN_CACHE_KEY)
            if cached_token:
                return str(cached_token)
        except Exception:
            pass

        response = await client.post(
            "/auth/login",
            data={
                "email": settings.eskiz_email,
                "password": settings.eskiz_password,
            },
        )
        if response.status_code >= 400:
            raise AppException(
                code="SMS_AUTH_FAILED",
                message="SMS provider avtorizatsiyasi amalga oshmadi.",
                status_code=502,
            )

        payload = response.json()
        token = payload.get("data", {}).get("token") or payload.get("token")
        if not token:
            raise AppException(
                code="SMS_AUTH_FAILED",
                message="SMS provider token qaytarmadi.",
                status_code=502,
            )
        token = str(token)

        try:
            await get_redis().setex(ESKIZ_TOKEN_CACHE_KEY, ESKIZ_TOKEN_TTL_SECONDS, token)
        except Exception:
            pass

        return token


def get_sms_provider() -> SmsProvider:
    if settings.sms_provider == SmsProviderType.ESKIZ.value:
        return EskizSmsProvider()
    return FakeSmsProvider()
