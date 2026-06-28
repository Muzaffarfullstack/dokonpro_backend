from sqlalchemy.orm import configure_mappers

from app.models import Product, StoreProduct


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


def test_store_products_link_a_store_to_one_global_product_once() -> None:
    unique_columns = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in StoreProduct.__table__.constraints
        if constraint.name and constraint.name.startswith("uq_store_products")
    }

    assert unique_columns["uq_store_products_store_product"] == ("store_id", "product_id")
    assert unique_columns["uq_store_products_store_local_sku"] == ("store_id", "local_sku")
