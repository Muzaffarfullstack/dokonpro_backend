from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Supplier
from app.modules.suppliers.repository import SuppliersRepository
from app.modules.suppliers.schemas import SupplierCreateRequest, SupplierUpdateRequest
from app.utils.pagination import build_pagination
from app.utils.phone import normalize_phone


class SuppliersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SuppliersRepository(db)

    async def list_suppliers(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> ApiListResponse[Supplier]:
        suppliers, total = await self.repo.list_suppliers(
            store_id=store_id,
            search=search,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(suppliers),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def create_supplier(
        self,
        *,
        store_id: uuid.UUID,
        payload: SupplierCreateRequest,
    ) -> Supplier:
        await self._ensure_unique_name(store_id=store_id, name=payload.name)
        supplier = await self.repo.create_supplier(
            store_id=store_id,
            name=payload.name,
            phone=self._phone(payload.phone),
            address=payload.address,
            note=payload.note,
        )
        await self.db.commit()
        return supplier

    async def get_supplier(self, *, store_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
        supplier = await self.repo.get_supplier(store_id=store_id, supplier_id=supplier_id)
        if supplier is None:
            raise AppException(
                code="SUPPLIER_NOT_FOUND",
                message="Yetkazib beruvchi topilmadi.",
                status_code=404,
            )
        return supplier

    async def update_supplier(
        self,
        *,
        store_id: uuid.UUID,
        supplier_id: uuid.UUID,
        payload: SupplierUpdateRequest,
    ) -> Supplier:
        supplier = await self.get_supplier(store_id=store_id, supplier_id=supplier_id)
        if payload.name is not None and payload.name != supplier.name:
            await self._ensure_unique_name(store_id=store_id, name=payload.name)
            supplier.name = payload.name
        if payload.phone is not None:
            supplier.phone = self._phone(payload.phone)
        if payload.address is not None:
            supplier.address = payload.address
        if payload.note is not None:
            supplier.note = payload.note
        await self.db.commit()
        return supplier

    async def deactivate_supplier(self, *, store_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
        supplier = await self.get_supplier(store_id=store_id, supplier_id=supplier_id)
        supplier.is_active = False
        await self.db.commit()

    async def _ensure_unique_name(self, *, store_id: uuid.UUID, name: str) -> None:
        if await self.repo.get_supplier_by_name(store_id=store_id, name=name):
            raise AppException(
                code="SUPPLIER_ALREADY_EXISTS",
                message="Bu nom bilan yetkazib beruvchi mavjud.",
                status_code=409,
                field="name",
            )

    def _phone(self, phone: str | None) -> str | None:
        return normalize_phone(phone) if phone else None
