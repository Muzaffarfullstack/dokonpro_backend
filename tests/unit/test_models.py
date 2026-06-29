from sqlalchemy.orm import configure_mappers

from app.models import Category, Product, Sale, Store, StoreProduct


def test_model_relationships_configure() -> None:
    configure_mappers()


def test_products_are_global_catalog_entries() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Product.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_products")
    }

    assert unique_columns["uq_products_slug"] == ("slug",)
    assert unique_columns["uq_products_barcode"] == ("barcode",)


def test_categories_are_global_catalog_taxonomy() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Category.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_categories")
    }

    assert "store_id" not in Category.__table__.columns
    assert unique_columns["uq_categories_slug"] == ("slug",)
    assert unique_columns["uq_categories_name"] == ("name",)


def test_store_products_link_a_store_to_one_global_product_once() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in StoreProduct.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_store_products")
    }

    assert unique_columns["uq_store_products_store_product"] == ("store_id", "product_id")
    assert unique_columns["uq_store_products_store_local_sku"] == ("store_id", "local_sku")
    assert "expiry_date" in StoreProduct.__table__.columns


def test_store_slug_is_unique_per_owner_not_globally() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Store.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_stores")
    }

    assert unique_columns["uq_stores_owner_slug"] == ("owner_id", "slug")


def test_sales_idempotency_key_is_unique_per_store() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in Sale.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_sales")
    }

    assert unique_columns["uq_sales_store_idempotency_key"] == ("store_id", "idempotency_key")
