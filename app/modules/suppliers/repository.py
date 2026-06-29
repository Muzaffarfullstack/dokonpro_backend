from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supplier


class SuppliersRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_supplier(self, *, store_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier | None:
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.store_id == store_id,
                Supplier.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_supplier_by_name(self, *, store_id: uuid.UUID, name: str) -> Supplier | None:
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.store_id == store_id,
                Supplier.name == name,
                Supplier.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    def _suppliers_query(
        self, *, store_id: uuid.UUID, search: str | None
    ) -> Select[tuple[Supplier]]:
        query = select(Supplier).where(Supplier.store_id == store_id, Supplier.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Supplier.name.ilike(pattern), Supplier.phone.ilike(pattern)))
        return query

    async def list_suppliers(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Supplier], int]:
        query = self._suppliers_query(store_id=store_id, search=search)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Supplier.name.asc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def create_supplier(
        self,
        *,
        store_id: uuid.UUID,
        name: str,
        phone: str | None,
        address: str | None,
        note: str | None,
    ) -> Supplier:
        supplier = Supplier(
            store_id=store_id,
            name=name,
            phone=phone,
            address=address,
            note=note,
        )
        self.db.add(supplier)
        await self.db.flush()
        return supplier

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
