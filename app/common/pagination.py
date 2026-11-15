"""Pagination + response envelopes per docs/06 §6.2–6.3."""
from typing import Any, Sequence

from fastapi import Query


def page_params(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return page, page_size


def paginate(items: Sequence, total: int, page: int, page_size: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": list(items),
        "meta": {"page": page, "page_size": page_size,
                 "total": total, "total_pages": total_pages},
    }


def ok(data: Any) -> dict:
    return {"data": data, "meta": None}


def ok_list(items: Sequence, total: int, page: int, page_size: int) -> dict:
    return paginate(items, total, page, page_size)
