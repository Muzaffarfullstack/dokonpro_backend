from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PurchaseStatus, StockMovementType
from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Purchase, StoreProduct, Supplier
from app.modules.purchases.repository import PurchasesRepository
from app.modules.purchases.schemas import (
    PurchaseCancelRequest,
    PurchaseCreateRequest,
    PurchaseItemCreateRequest,
)
from app.utils.pagination import build_pagination

MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class PreparedPurchaseItem:
    payload: PurchaseItemCreateRequest
    store_product: StoreProduct
    total_amount: Decimal


class PurchasesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PurchasesRepository(db)

    async def create_purchase(
        self,
        *,
        store_id: uuid.UUID,
        payload: PurchaseCreateRequest,
    ) -> Purchase:
        self._ensure_unique_items(payload.items)
        supplier = await self._supplier(store_id=store_id, supplier_id=payload.supplier_id)
        prepared_items = await self._prepare_items(store_id=store_id, items=payload.items)
        total_amount = self._money(sum(item.total_amount for item in prepared_items))
        paid_amount = min(self._money(payload.paid_amount), total_amount)

        purchase = await self.repo.create_purchase(
            store_id=store_id,
            supplier_id=supplier.id if supplier else None,
            total_amount=total_amount,
            paid_amount=paid_amount,
            status=PurchaseStatus.COMPLETED.value,
            note=payload.note,
        )

        for item in prepared_items:
            item.store_product.stock_quantity += item.payload.quantity
            item.store_product.cost_price = self._money(item.payload.unit_cost)
            await self.repo.create_purchase_item(
                store_id=store_id,
                purchase_id=purchase.id,
                store_product_id=item.store_product.id,
                product_name=item.store_product.product.name,
                quantity=item.payload.quantity,
                unit_cost=self._money(item.payload.unit_cost),
                total_amount=item.total_amount,
            )
            await self.repo.create_stock_movement(
                store_id=store_id,
                store_product_id=item.store_product.id,
                movement_type=StockMovementType.IN.value,
                quantity=item.payload.quantity,
                unit_cost=self._money(item.payload.unit_cost),
                reason="purchase",
                note=payload.note,
            )

        if supplier is not None:
            supplier.balance += self._money(total_amount - paid_amount)

        await self.db.commit()
        persisted_purchase = await self.repo.get_purchase(
            store_id=store_id, purchase_id=purchase.id
        )
        return persisted_purchase or purchase

    async def cancel_purchase(
        self,
        *,
        store_id: uuid.UUID,
        purchase_id: uuid.UUID,
        payload: PurchaseCancelRequest,
    ) -> Purchase:
        purchase = await self.repo.get_purchase_for_update(
            store_id=store_id, purchase_id=purchase_id
        )
        if purchase is None:
            raise AppException(
                code="PURCHASE_NOT_FOUND",
                message="Kirim topilmadi.",
                status_code=404,
            )
        if purchase.status == PurchaseStatus.CANCELLED.value:
            raise AppException(
                code="PURCHASE_ALREADY_CANCELLED",
                message="Kirim allaqachon bekor qilingan.",
                status_code=409,
            )

        for item in purchase.items:
            store_product = await self.repo.get_store_product_for_update(
                store_id=store_id,
                store_product_id=item.store_product_id,
            )
            if store_product is None:
                raise AppException(
                    code="STORE_PRODUCT_NOT_FOUND",
                    message="Do'kon mahsuloti topilmadi.",
                    status_code=404,
                )
            if store_product.stock_quantity < item.quantity:
                raise AppException(
                    code="INSUFFICIENT_STOCK_TO_CANCEL_PURCHASE",
                    message="Kirimni bekor qilish uchun omborda mahsulot yetarli emas.",
                    status_code=409,
                    details={"store_product_id": str(item.store_product_id)},
                )
            store_product.stock_quantity -= item.quantity
            await self.repo.create_stock_movement(
                store_id=store_id,
                store_product_id=item.store_product_id,
                movement_type=StockMovementType.OUT.value,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                reason="purchase_cancel",
                note=payload.note,
            )

        supplier = await self._supplier(store_id=store_id, supplier_id=purchase.supplier_id)
        if supplier is not None:
            supplier.balance = max(Decimal("0"), supplier.balance - self._unpaid_amount(purchase))
        purchase.status = PurchaseStatus.CANCELLED.value
        await self.db.commit()
        persisted_purchase = await self.repo.get_purchase(
            store_id=store_id, purchase_id=purchase.id
        )
        return persisted_purchase or purchase

    async def get_purchase(self, *, store_id: uuid.UUID, purchase_id: uuid.UUID) -> Purchase:
        purchase = await self.repo.get_purchase(store_id=store_id, purchase_id=purchase_id)
        if purchase is None:
            raise AppException(
                code="PURCHASE_NOT_FOUND",
                message="Kirim topilmadi.",
                status_code=404,
            )
        return purchase

    async def list_purchases(
        self,
        *,
        store_id: uuid.UUID,
        status: PurchaseStatus | None,
        page: int,
        limit: int,
    ) -> ApiListResponse[Purchase]:
        purchases, total = await self.repo.list_purchases(
            store_id=store_id,
            status=status.value if status else None,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(purchases),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def _supplier(
        self,
        *,
        store_id: uuid.UUID,
        supplier_id: uuid.UUID | None,
    ) -> Supplier | None:
        if supplier_id is None:
            return None
        supplier = await self.repo.get_supplier_for_update(
            store_id=store_id, supplier_id=supplier_id
        )
        if supplier is None:
            raise AppException(
                code="SUPPLIER_NOT_FOUND",
                message="Yetkazib beruvchi topilmadi.",
                status_code=404,
                field="supplier_id",
            )
        return supplier

    async def _prepare_items(
        self,
        *,
        store_id: uuid.UUID,
        items: list[PurchaseItemCreateRequest],
    ) -> list[PreparedPurchaseItem]:
        prepared_items: list[PreparedPurchaseItem] = []
        for item in items:
            store_product = await self.repo.get_store_product_for_update(
                store_id=store_id,
                store_product_id=item.store_product_id,
            )
            if store_product is None:
                raise AppException(
                    code="STORE_PRODUCT_NOT_FOUND",
                    message="Do'kon mahsuloti topilmadi.",
                    status_code=404,
                    field="store_product_id",
                )
            prepared_items.append(
                PreparedPurchaseItem(
                    payload=item,
                    store_product=store_product,
                    total_amount=self._money(item.quantity * item.unit_cost),
                )
            )
        return prepared_items

    def _ensure_unique_items(self, items: list[PurchaseItemCreateRequest]) -> None:
        product_ids = [item.store_product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise AppException(
                code="DUPLICATE_PURCHASE_ITEM",
                message="Bitta mahsulot kirimda bir marta berilishi kerak.",
                status_code=400,
                field="items",
            )

    def _unpaid_amount(self, purchase: Purchase) -> Decimal:
        return self._money(max(Decimal("0"), purchase.total_amount - purchase.paid_amount))

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
