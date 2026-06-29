from fastapi.testclient import TestClient

from app.main import app


def test_products_routes_are_registered() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/products/categories" in paths
    assert "/api/v1/products/catalog" in paths
    assert "/api/v1/products" in paths
    assert "/api/v1/products/{store_product_id}" in paths
    assert "/api/v1/products/{store_product_id}/stock" in paths
    assert paths["/api/v1/products/catalog"]["post"]["tags"] == ["products"]


def test_products_write_routes_expose_csrf_header() -> None:
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    post_catalog = schema["paths"]["/api/v1/products/catalog"]["post"]
    post_inventory = schema["paths"]["/api/v1/products"]["post"]
    post_stock = schema["paths"]["/api/v1/products/{store_product_id}/stock"]["post"]

    assert any(param["name"] == "x-csrf-token" for param in post_catalog["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in post_inventory["parameters"])
    assert any(param["name"] == "x-csrf-token" for param in post_stock["parameters"])


def test_products_read_routes_require_login() -> None:
    client = TestClient(app)

    catalog_response = client.get("/api/v1/products/catalog")
    categories_response = client.get("/api/v1/products/categories")

    assert catalog_response.status_code == 401
    assert categories_response.status_code == 401
    assert catalog_response.json()["error"]["code"] == "UNAUTHORIZED"
    assert categories_response.json()["error"]["code"] == "UNAUTHORIZED"
