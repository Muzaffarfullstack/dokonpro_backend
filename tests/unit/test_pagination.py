from app.utils.pagination import build_pagination


def test_build_pagination_calculates_pages() -> None:
    pagination = build_pagination(page=2, limit=20, total=41)

    assert pagination.page == 2
    assert pagination.limit == 20
    assert pagination.total == 41
    assert pagination.pages == 3


def test_build_pagination_handles_zero_limit() -> None:
    pagination = build_pagination(page=1, limit=0, total=10)

    assert pagination.pages == 0
