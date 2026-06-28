from app.utils.slug import slugify


def test_slugify_normalizes_value() -> None:
    assert slugify("  Coca Cola 0.5L  ") == "coca-cola-0-5l"


def test_slugify_supports_uzbek_latin_letters() -> None:
    assert slugify("G'alla Do'koni") == "galla-dokoni"
    assert slugify("Qo'qon Go'sht Markazi") == "qoqon-gosht-markazi"


def test_slugify_transliterates_cyrillic() -> None:
    assert slugify("Азиз магазин") == "aziz-magazin"
    assert slugify("Қўқон савдо маркази") == "qoqon-savdo-markazi"
