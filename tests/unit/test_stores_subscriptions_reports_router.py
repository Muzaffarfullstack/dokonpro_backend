from fastapi.testclient import TestClient

from app.main import app


def test_stores_subscriptions_and_reports_routes_are_registered() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/stores" in paths
    assert "/api/v1/stores/{store_id}" in paths
    assert "/api/v1/subscriptions/current" in paths
    assert "/api/v1/subscriptions/activate" in paths
    assert "/api/v1/subscriptions/cancel" in paths
    assert "/api/v1/reports/summary" in paths
    assert "/api/v1/reports/sales" in paths
    assert "/api/v1/reports/profit" in paths
    assert "/api/v1/reports/stock" in paths
    assert "/api/v1/reports/debts" in paths


def test_store_and_subscription_write_routes_expose_csrf_header() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    create_store = schema["paths"]["/api/v1/stores"]["post"]
    update_store = schema["paths"]["/api/v1/stores/{store_id}"]["patch"]
    activate_subscription = schema["paths"]["/api/v1/subscriptions/activate"]["post"]

    assert any(param["name"] == "x-csrf-token" for param in create_store["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in update_store["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in activate_subscription["parameters"])
