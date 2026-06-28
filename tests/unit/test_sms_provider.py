import pytest

from app.integrations.sms import ESKIZ_TOKEN_CACHE_KEY, EskizSmsProvider


class FakeRedis:
    def __init__(self, cached_token: str | None = None) -> None:
        self.cached_token = cached_token
        self.saved: tuple[str, int, str] | None = None

    async def get(self, key: str) -> str | None:
        assert key == ESKIZ_TOKEN_CACHE_KEY
        return self.cached_token

    async def setex(self, key: str, seconds: int, value: str) -> None:
        self.saved = (key, seconds, value)


class FakeResponse:
    status_code = 200

    def json(self) -> dict[str, dict[str, str]]:
        return {"data": {"token": "fresh-token"}}


class FakeHttpClient:
    def __init__(self) -> None:
        self.posts = 0

    async def post(self, _: str, data: dict[str, str]) -> FakeResponse:
        self.posts += 1
        assert data["email"]
        assert data["password"]
        return FakeResponse()


@pytest.mark.asyncio
async def test_eskiz_token_uses_redis_cache(monkeypatch) -> None:
    from app.integrations import sms

    client = FakeHttpClient()
    monkeypatch.setattr(sms, "get_redis", lambda: FakeRedis(cached_token="cached-token"))

    token = await EskizSmsProvider()._get_token(client)

    assert token == "cached-token"
    assert client.posts == 0


@pytest.mark.asyncio
async def test_eskiz_token_is_cached_after_login(monkeypatch) -> None:
    from app.integrations import sms

    redis = FakeRedis()
    client = FakeHttpClient()
    monkeypatch.setattr(sms, "get_redis", lambda: redis)
    monkeypatch.setattr(sms.settings, "eskiz_email", "user@example.com")
    monkeypatch.setattr(sms.settings, "eskiz_password", "secret")

    token = await EskizSmsProvider()._get_token(client)

    assert token == "fresh-token"
    assert client.posts == 1
    assert redis.saved is not None
    assert redis.saved[0] == ESKIZ_TOKEN_CACHE_KEY
    assert redis.saved[2] == "fresh-token"
