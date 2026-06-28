import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.enums import SubscriptionStatus, UserRole
from app.core.security import ACCESS_TOKEN_COOKIE, CSRF_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE
from app.main import app
from app.modules.auth.schemas import AuthResponse, AuthStoreResponse, UserResponse
from app.modules.auth.service import AuthSession


class FakeAuthService:
    def __init__(self, _: object) -> None:
        pass

    async def register(self, _: object) -> AuthSession:
        user_id = uuid.uuid4()
        store_id = uuid.uuid4()
        csrf_token = "csrf-test-token"
        return AuthSession(
            access_token="access-test-token",
            refresh_token="refresh-test-token",
            response=AuthResponse(
                user=UserResponse(
                    id=user_id,
                    full_name="Ali Valiyev",
                    phone="+998901234567",
                    role=UserRole.OWNER.value,
                ),
                stores=[
                    AuthStoreResponse(
                        id=store_id,
                        name="Asaka Savdo Markazi",
                        read_only=False,
                        subscription_status=SubscriptionStatus.TRIALING.value,
                        trial_ends_at=datetime.now(UTC) + timedelta(days=7),
                    )
                ],
                active_store=AuthStoreResponse(
                    id=store_id,
                    name="Asaka Savdo Markazi",
                    read_only=False,
                    subscription_status=SubscriptionStatus.TRIALING.value,
                    trial_ends_at=datetime.now(UTC) + timedelta(days=7),
                ),
                requires_store_selection=False,
                csrf_token=csrf_token,
            ),
        )


def test_register_sets_httponly_access_cookie_and_csrf_cookie(monkeypatch) -> None:
    from app.modules.auth import router as auth_router

    monkeypatch.setattr(auth_router, "AuthService", FakeAuthService)
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Ali",
            "last_name": "Valiyev",
            "store_name": "Asaka Savdo Markazi",
            "phone": "+998 90 123 45 67",
            "password": "secret123",
            "password_confirm": "secret123",
            "otp_code": "123456",
        },
    )

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert f"{ACCESS_TOKEN_COOKIE}=access-test-token" in set_cookie
    assert f"{REFRESH_TOKEN_COOKIE}=refresh-test-token" in set_cookie
    assert "HttpOnly" in set_cookie
    assert f"{CSRF_TOKEN_COOKIE}=csrf-test-token" in set_cookie
    assert (
        response.json()["data"]["stores"][0]["subscription_status"]
        == SubscriptionStatus.TRIALING.value
    )
