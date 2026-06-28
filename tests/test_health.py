from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_shape() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code in {200, 503}
    body = response.json()
    assert body["success"] is True
    assert body["data"]["api"] == "ok"
    assert body["data"]["database"] in {"ok", "error"}
    assert body["data"]["redis"] in {"ok", "error"}
    if "error" in {body["data"]["database"], body["data"]["redis"]}:
        assert response.status_code == 503


def test_health_endpoint_returns_503_when_redis_is_down(monkeypatch) -> None:
    from app.api.v1 import router as api_router

    class FakeSession:
        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def execute(self, _: object) -> None:
            return None

    class FakeRedis:
        async def ping(self) -> None:
            raise ConnectionError

    monkeypatch.setattr(api_router, "async_session_maker", lambda: FakeSession())
    monkeypatch.setattr(api_router, "get_redis", lambda: FakeRedis())

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["data"] == {"api": "ok", "database": "ok", "redis": "error"}
