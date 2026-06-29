from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DebtTransactionType, PaymentStatus
from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Debtor, DebtTransaction
from app.modules.debts.repository import DebtsRepository
from app.modules.debts.schemas import (
    DebtAdjustmentRequest,
    DebtBorrowRequest,
    DebtorCreateRequest,
    DebtorUpdateRequest,
    DebtRepaymentRequest,
)
from app.utils.pagination import build_pagination
from app.utils.phone import normalize_phone

MONEY_QUANT = Decimal("0.01")


class DebtsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DebtsRepository(db)

    async def create_debtor(self, *, store_id: uuid.UUID, payload: DebtorCreateRequest) -> Debtor:
        phone = normalize_phone(payload.phone)
        if await self.repo.get_debtor_by_phone(store_id=store_id, phone=phone):
            raise AppException(
                code="DEBTOR_PHONE_EXISTS",
                message="Bu telefon raqam bilan qarzdor mavjud.",
                status_code=409,
                field="phone",
            )

        debtor = await self.repo.create_debtor(
            store_id=store_id,
            name=payload.name,
            phone=phone,
            address=payload.address,
            note=payload.note,
        )
        await self.db.commit()
        return debtor

    async def list_debtors(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> ApiListResponse[Debtor]:
        debtors, total = await self.repo.list_debtors(
            store_id=store_id,
            search=search,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(debtors),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def get_debtor(self, *, store_id: uuid.UUID, debtor_id: uuid.UUID) -> Debtor:
        debtor = await self.repo.get_debtor(store_id=store_id, debtor_id=debtor_id)
        if debtor is None:
            raise AppException(
                code="DEBTOR_NOT_FOUND",
                message="Qarzdor topilmadi.",
                status_code=404,
            )
        return debtor

    async def update_debtor(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        payload: DebtorUpdateRequest,
    ) -> Debtor:
        debtor = await self.get_debtor(store_id=store_id, debtor_id=debtor_id)

        if payload.phone:
            phone = normalize_phone(payload.phone)
            if phone != debtor.phone:
                existing = await self.repo.get_debtor_by_phone(store_id=store_id, phone=phone)
                if existing is not None:
                    raise AppException(
                        code="DEBTOR_PHONE_EXISTS",
                        message="Bu telefon raqam bilan qarzdor mavjud.",
                        status_code=409,
                        field="phone",
                    )
                debtor.phone = phone

        for field in ("name", "address", "note"):
            value = getattr(payload, field)
            if value is not None:
                setattr(debtor, field, value)

        await self.db.commit()
        return debtor

    async def deactivate_debtor(self, *, store_id: uuid.UUID, debtor_id: uuid.UUID) -> None:
        debtor = await self.get_debtor(store_id=store_id, debtor_id=debtor_id)
        if debtor.balance > 0:
            raise AppException(
                code="DEBTOR_HAS_BALANCE",
                message="Balansi bor qarzdorni o'chirib bo'lmaydi.",
                status_code=409,
            )
        debtor.is_active = False
        await self.db.commit()

    async def borrow(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        payload: DebtBorrowRequest,
    ) -> DebtTransaction:
        debtor = await self._get_debtor_for_update(store_id=store_id, debtor_id=debtor_id)
        amount = self._money(payload.amount)

        linked_sale = (
            await self.repo.get_sale(store_id=store_id, sale_id=payload.sale_id)
            if payload.sale_id
            else None
        )
        if payload.sale_id and linked_sale is None:
            raise AppException(
                code="SALE_NOT_FOUND",
                message="Sotuv topilmadi.",
                status_code=404,
                field="sale_id",
            )

        debtor.balance = self._money(debtor.balance + amount)
        transaction = await self.repo.create_transaction(
            store_id=store_id,
            debtor_id=debtor.id,
            transaction_type=DebtTransactionType.BORROW.value,
            amount=amount,
            sale_id=payload.sale_id,
            note=payload.note,
        )
        await self.db.commit()
        return transaction

    async def repay(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        payload: DebtRepaymentRequest,
    ) -> DebtTransaction:
        debtor = await self._get_debtor_for_update(store_id=store_id, debtor_id=debtor_id)
        amount = self._money(payload.amount)
        if amount > debtor.balance:
            raise AppException(
                code="PAYMENT_EXCEEDS_BALANCE",
                message="To'lov qarz balansidan katta bo'lishi mumkin emas.",
                status_code=409,
                field="amount",
            )

        debtor.balance = self._money(debtor.balance - amount)
        transaction = await self.repo.create_transaction(
            store_id=store_id,
            debtor_id=debtor.id,
            transaction_type=DebtTransactionType.REPAYMENT.value,
            amount=amount,
            sale_id=None,
            note=payload.note,
        )
        payment = await self.repo.create_payment(
            store_id=store_id,
            debt_transaction_id=transaction.id,
            amount=amount,
            method=payload.method.value,
            status=PaymentStatus.COMPLETED.value,
            reference=payload.reference,
            note=payload.note,
        )
        transaction.payments = [payment]
        await self.db.commit()
        return transaction

    async def adjust(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        payload: DebtAdjustmentRequest,
    ) -> DebtTransaction:
        debtor = await self._get_debtor_for_update(store_id=store_id, debtor_id=debtor_id)
        new_balance = self._money(payload.new_balance)
        difference = abs(self._money(new_balance - debtor.balance))
        if difference == 0:
            raise AppException(
                code="BALANCE_UNCHANGED",
                message="Yangi balans hozirgi balans bilan bir xil.",
                status_code=400,
                field="new_balance",
            )

        old_balance = debtor.balance
        debtor.balance = new_balance
        note = payload.note or f"Balance adjusted from {old_balance} to {new_balance}"
        transaction = await self.repo.create_transaction(
            store_id=store_id,
            debtor_id=debtor.id,
            transaction_type=DebtTransactionType.ADJUSTMENT.value,
            amount=difference,
            sale_id=None,
            note=note,
        )
        await self.db.commit()
        return transaction

    async def list_transactions(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> ApiListResponse[DebtTransaction]:
        await self.get_debtor(store_id=store_id, debtor_id=debtor_id)
        transactions, total = await self.repo.list_transactions(
            store_id=store_id,
            debtor_id=debtor_id,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(transactions),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def _get_debtor_for_update(self, *, store_id: uuid.UUID, debtor_id: uuid.UUID) -> Debtor:
        debtor = await self.repo.get_debtor_for_update(store_id=store_id, debtor_id=debtor_id)
        if debtor is None:
            raise AppException(
                code="DEBTOR_NOT_FOUND",
                message="Qarzdor topilmadi.",
                status_code=404,
            )
        return debtor

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
