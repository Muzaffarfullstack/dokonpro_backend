from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_and_settings_routes_are_registered() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/dashboard/summary" in paths
    assert "/api/v1/settings/store" in paths
    assert "/api/v1/settings/account" in paths
    assert "/api/v1/settings/security" in paths
    assert "/api/v1/settings/security/password" in paths
    assert "/api/v1/settings/billing" in paths
    assert "/api/v1/settings/notifications" in paths


def test_settings_write_route_exposes_csrf_header() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    update_settings = schema["paths"]["/api/v1/settings/store"]["patch"]
    update_account = schema["paths"]["/api/v1/settings/account"]["patch"]
    change_password = schema["paths"]["/api/v1/settings/security/password"]["post"]

    assert any(param["name"] == "x-csrf-token" for param in update_settings["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in update_account["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in change_password["parameters"])
