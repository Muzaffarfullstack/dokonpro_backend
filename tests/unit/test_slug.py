from app.utils.slug import slugify


def test_slugify_normalizes_value() -> None:
    assert slugify("  Coca Cola 0.5L  ") == "coca-cola-0-5l"
