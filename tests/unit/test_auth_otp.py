import pytest

from app.core.enums import OtpPurpose
from app.core.exceptions import AppException
from app.modules.auth.otp import OtpService


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def exists(self, key: str) -> bool:
        return key in self.data

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -1)

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self.data[key] = value
        self.ttls[key] = seconds

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def incr(self, key: str) -> int:
        value = int(self.data.get(key, "0")) + 1
        self.data[key] = str(value)
        return value

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.data:
                deleted += 1
                self.data.pop(key)
                self.ttls.pop(key, None)
        return deleted


class FakeSmsProvider:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def send_sms(self, *, phone: str, message: str) -> None:
        self.messages.append((phone, message))


@pytest.fixture
def otp_service(monkeypatch) -> tuple[OtpService, FakeRedis, FakeSmsProvider]:
    redis = FakeRedis()
    provider = FakeSmsProvider()
    service = OtpService(provider=provider)
    service.redis = redis

    from app.modules.auth import otp as otp_module

    monkeypatch.setattr(otp_module.settings, "sms_provider", "fake")
    return service, redis, provider


@pytest.mark.asyncio
async def test_send_code_stores_hash_and_sends_sms(otp_service) -> None:
    service, redis, provider = otp_service

    result = await service.send_code(phone="+1 555 111 2233", purpose=OtpPurpose.REGISTER)

    assert result.phone == "+15551112233"
    assert result.debug_code is not None
    assert provider.messages
    assert "+15551112233" == provider.messages[0][0]
    assert f"otp:{OtpPurpose.REGISTER.value}:+15551112233:code" in redis.data
    assert result.debug_code not in redis.data.values()


@pytest.mark.asyncio
async def test_send_code_respects_resend_cooldown(otp_service) -> None:
    service, _, _ = otp_service

    await service.send_code(phone="+15551112233", purpose=OtpPurpose.REGISTER)

    with pytest.raises(AppException) as exc:
        await service.send_code(phone="+15551112233", purpose=OtpPurpose.REGISTER)

    assert exc.value.code == "OTP_RESEND_COOLDOWN"
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_verify_code_returns_one_time_verification_token(otp_service) -> None:
    service, redis, _ = otp_service

    send_result = await service.send_code(phone="+15551112233", purpose=OtpPurpose.REGISTER)
    verify_result = await service.verify_code(
        phone="+15551112233",
        purpose=OtpPurpose.REGISTER,
        code=send_result.debug_code,
    )

    assert verify_result.phone == "+15551112233"
    assert verify_result.verification_token
    verified_key = (
        f"otp:{OtpPurpose.REGISTER.value}:+15551112233:"
        f"verified:{verify_result.verification_token}"
    )
    assert verified_key in redis.data

    consumed_phone = await service.consume_verification(
        phone="+15551112233",
        purpose=OtpPurpose.REGISTER,
        verification_token=verify_result.verification_token,
    )
    assert consumed_phone == "+15551112233"

    with pytest.raises(AppException) as exc:
        await service.consume_verification(
            phone="+15551112233",
            purpose=OtpPurpose.REGISTER,
            verification_token=verify_result.verification_token,
        )
    assert exc.value.code == "PHONE_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_consume_code_verifies_and_removes_code(otp_service) -> None:
    service, redis, _ = otp_service

    send_result = await service.send_code(phone="+15551112233", purpose=OtpPurpose.REGISTER)
    consumed_phone = await service.consume_code(
        phone="+15551112233",
        purpose=OtpPurpose.REGISTER,
        code=send_result.debug_code,
    )

    assert consumed_phone == "+15551112233"
    assert f"otp:{OtpPurpose.REGISTER.value}:+15551112233:code" not in redis.data


@pytest.mark.asyncio
async def test_verify_code_rejects_invalid_code(otp_service) -> None:
    service, _, _ = otp_service

    await service.send_code(phone="+15551112233", purpose=OtpPurpose.PASSWORD_RESET)

    with pytest.raises(AppException) as exc:
        await service.verify_code(
            phone="+15551112233",
            purpose=OtpPurpose.PASSWORD_RESET,
            code="000000",
        )

    assert exc.value.code == "OTP_INVALID"
