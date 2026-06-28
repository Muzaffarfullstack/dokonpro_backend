from fastapi.testclient import TestClient

from app.core.exceptions import AppException
from app.main import app


@app.get("/__test__/exception")
async def raise_test_exception() -> None:
    raise AppException(code="TEST_ERROR", message="Test error", status_code=418, field="name")


def test_app_exception_handler_returns_standard_error_shape() -> None:
    client = TestClient(app)
    response = client.get("/__test__/exception")

    assert response.status_code == 418
    assert response.json() == {
        "success": False,
        "error": {
            "code": "TEST_ERROR",
            "message": "Test error",
            "field": "name",
            "details": {},
        },
    }
