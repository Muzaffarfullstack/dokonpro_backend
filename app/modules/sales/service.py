from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PaymentStatus, SalePaymentStatus, SaleStatus, StockMovementType
from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Sale, StoreProduct
from app.modules.sales.repository import SalesRepository
from app.modules.sales.schemas import SaleCheckoutItemRequest, SaleCheckoutRequest
from app.utils.pagination import build_pagination

MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class PreparedSaleItem:
    payload: SaleCheckoutItemRequest
    store_product: StoreProduct
    unit_price: Decimal
    gross_amount: Decimal
    total_amount: Decimal


class SalesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SalesRepository(db)

    async def checkout(self, *, store_id: uuid.UUID, payload: SaleCheckoutRequest) -> Sale:
        self._ensure_unique_items(payload.items)
        prepared_items = await self._prepare_items(store_id=store_id, items=payload.items)

        subtotal = self._money(sum(item.gross_amount for item in prepared_items))
        item_discount_total = self._money(
            sum(item.payload.discount_amount for item in prepared_items)
        )
        if item_discount_total > subtotal:
            raise AppException(
                code="INVALID_DISCOUNT",
                message="Chegirma mahsulotlar summasidan katta bo'lishi mumkin emas.",
                status_code=400,
                field="items",
            )

        order_discount = self._money(payload.discount_amount)
        discount_base = subtotal - item_discount_total
        if order_discount > discount_base:
            raise AppException(
                code="INVALID_DISCOUNT",
                message="Umumiy chegirma sotuv summasidan katta bo'lishi mumkin emas.",
                status_code=400,
                field="discount_amount",
            )

        discount_total = self._money(item_discount_total + order_discount)
        total_amount = self._money(subtotal - discount_total)
        paid_applied = min(self._money(payload.paid_amount), total_amount)
        change_amount = self._money(max(payload.paid_amount - total_amount, Decimal("0")))
        payment_status = self._payment_status(paid_amount=paid_applied, total_amount=total_amount)

        sale = await self.repo.create_sale(
            store_id=store_id,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone,
            status=SaleStatus.COMPLETED.value,
            payment_status=payment_status.value,
            subtotal=subtotal,
            discount_total=discount_total,
            total_amount=total_amount,
            paid_amount=paid_applied,
            change_amount=change_amount,
            note=payload.note,
        )

        for item in prepared_items:
            item.store_product.stock_quantity -= item.payload.quantity
            await self.repo.create_sale_item(
                store_id=store_id,
                sale_id=sale.id,
                store_product_id=item.store_product.id,
                product_name=item.store_product.product.name,
                local_sku=item.store_product.local_sku,
                quantity=item.payload.quantity,
                unit_price=item.unit_price,
                discount_amount=self._money(item.payload.discount_amount),
                total_amount=item.total_amount,
            )
            await self.repo.create_stock_movement(
                store_id=store_id,
                store_product_id=item.store_product.id,
                sale_id=sale.id,
                movement_type=StockMovementType.OUT.value,
                quantity=-item.payload.quantity,
                unit_cost=item.store_product.cost_price,
                reason="sale",
                note=None,
            )

        if paid_applied > 0:
            await self.repo.create_payment(
                store_id=store_id,
                sale_id=sale.id,
                amount=paid_applied,
                method=payload.payment_method.value,
                status=PaymentStatus.COMPLETED.value,
                reference=payload.payment_reference,
                note=payload.note,
            )

        await self.db.commit()
        persisted_sale = await self.repo.get_sale(store_id=store_id, sale_id=sale.id)
        return persisted_sale or sale

    async def get_sale(self, *, store_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
        sale = await self.repo.get_sale(store_id=store_id, sale_id=sale_id)
        if sale is None:
            raise AppException(code="SALE_NOT_FOUND", message="Sotuv topilmadi.", status_code=404)
        return sale

    async def list_sales(
        self,
        *,
        store_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> ApiListResponse[Sale]:
        sales, total = await self.repo.list_sales(store_id=store_id, page=page, limit=limit)
        return ApiListResponse(
            data=list(sales),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def _prepare_items(
        self,
        *,
        store_id: uuid.UUID,
        items: list[SaleCheckoutItemRequest],
    ) -> list[PreparedSaleItem]:
        prepared_items: list[PreparedSaleItem] = []
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

            if store_product.stock_quantity < item.quantity:
                raise AppException(
                    code="INSUFFICIENT_STOCK",
                    message="Omborda yetarli mahsulot yo'q.",
                    status_code=409,
                    field="quantity",
                    details={
                        "store_product_id": str(item.store_product_id),
                        "available": str(store_product.stock_quantity),
                    },
                )

            unit_price = self._money(store_product.sale_price)
            gross_amount = self._money(unit_price * item.quantity)
            discount_amount = self._money(item.discount_amount)
            if discount_amount > gross_amount:
                raise AppException(
                    code="INVALID_DISCOUNT",
                    message="Mahsulot chegirmasi mahsulot summasidan katta bo'lishi mumkin emas.",
                    status_code=400,
                    field="discount_amount",
                )

            prepared_items.append(
                PreparedSaleItem(
                    payload=item,
                    store_product=store_product,
                    unit_price=unit_price,
                    gross_amount=gross_amount,
                    total_amount=self._money(gross_amount - discount_amount),
                )
            )
        return prepared_items

    def _ensure_unique_items(self, items: list[SaleCheckoutItemRequest]) -> None:
        product_ids = [item.store_product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise AppException(
                code="DUPLICATE_SALE_ITEM",
                message="Bitta mahsulot sotuvda bir marta berilishi kerak.",
                status_code=400,
                field="items",
            )

    def _payment_status(
        self,
        *,
        paid_amount: Decimal,
        total_amount: Decimal,
    ) -> SalePaymentStatus:
        if total_amount == 0 or paid_amount >= total_amount:
            return SalePaymentStatus.PAID
        if paid_amount > 0:
            return SalePaymentStatus.PARTIAL
        return SalePaymentStatus.UNPAID

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
