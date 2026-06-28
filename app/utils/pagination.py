from math import ceil

from app.core.responses import Pagination


def build_pagination(page: int, limit: int, total: int) -> Pagination:
    pages = ceil(total / limit) if limit > 0 else 0
    return Pagination(page=page, limit=limit, total=total, pages=pages)
