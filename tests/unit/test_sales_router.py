from fastapi.testclient import TestClient

from app.main import app


def test_sales_routes_are_registered() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/sales" in paths
    assert "/api/v1/sales/{sale_id}" in paths
    assert "/api/v1/sales/{sale_id}/cancel" in paths
    assert paths["/api/v1/sales"]["post"]["tags"] == ["sales"]


def test_sales_routes_require_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/sales")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_sales_checkout_exposes_csrf_header() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    checkout = schema["paths"]["/api/v1/sales"]["post"]
    cancel = schema["paths"]["/api/v1/sales/{sale_id}/cancel"]["post"]

    assert any(param["name"] == "x-csrf-token" for param in checkout["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in cancel["parameters"])
