from fastapi.testclient import TestClient

from app.main import app


def test_debts_routes_are_registered() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/debts" in paths
    assert "/api/v1/debts/{debtor_id}" in paths
    assert "/api/v1/debts/{debtor_id}/borrow" in paths
    assert "/api/v1/debts/{debtor_id}/repay" in paths
    assert "/api/v1/debts/{debtor_id}/adjust" in paths
    assert "/api/v1/debts/{debtor_id}/transactions" in paths


def test_debts_routes_require_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/debts")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_debts_write_routes_expose_csrf_header() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    create_debtor = schema["paths"]["/api/v1/debts"]["post"]
    borrow = schema["paths"]["/api/v1/debts/{debtor_id}/borrow"]["post"]
    repay = schema["paths"]["/api/v1/debts/{debtor_id}/repay"]["post"]

    assert any(param["name"] == "x-csrf-token" for param in create_debtor["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in borrow["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in repay["parameters"])
