from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Debtor, DebtTransaction, Payment, Sale


class DebtsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_debtor_by_phone(self, *, store_id: uuid.UUID, phone: str) -> Debtor | None:
        result = await self.db.execute(
            select(Debtor).where(
                Debtor.store_id == store_id,
                Debtor.phone == phone,
                Debtor.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_debtor(self, *, store_id: uuid.UUID, debtor_id: uuid.UUID) -> Debtor | None:
        result = await self.db.execute(
            select(Debtor)
            .options(
                selectinload(Debtor.transactions).selectinload(DebtTransaction.payments),
            )
            .where(
                Debtor.id == debtor_id,
                Debtor.store_id == store_id,
                Debtor.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_debtor_for_update(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
    ) -> Debtor | None:
        result = await self.db.execute(
            select(Debtor)
            .where(
                Debtor.id == debtor_id,
                Debtor.store_id == store_id,
                Debtor.is_active.is_(True),
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    def _debtors_query(self, *, store_id: uuid.UUID, search: str | None) -> Select[tuple[Debtor]]:
        query = select(Debtor).where(Debtor.store_id == store_id, Debtor.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Debtor.name.ilike(pattern), Debtor.phone.ilike(pattern)))
        return query

    async def list_debtors(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Debtor], int]:
        query = self._debtors_query(store_id=store_id, search=search)
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Debtor.name.asc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def create_debtor(
        self,
        *,
        store_id: uuid.UUID,
        name: str,
        phone: str,
        address: str | None,
        note: str | None,
    ) -> Debtor:
        debtor = Debtor(
            store_id=store_id,
            name=name,
            phone=phone,
            address=address,
            note=note,
            balance=Decimal("0"),
        )
        self.db.add(debtor)
        await self.db.flush()
        return debtor

    async def get_sale(self, *, store_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
        result = await self.db.execute(
            select(Sale).where(Sale.id == sale_id, Sale.store_id == store_id)
        )
        return result.scalar_one_or_none()

    async def create_transaction(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        transaction_type: str,
        amount: Decimal,
        sale_id: uuid.UUID | None,
        note: str | None,
    ) -> DebtTransaction:
        transaction = DebtTransaction(
            store_id=store_id,
            debtor_id=debtor_id,
            transaction_type=transaction_type,
            amount=amount,
            sale_id=sale_id,
            note=note,
        )
        self.db.add(transaction)
        await self.db.flush()
        return transaction

    async def create_payment(
        self,
        *,
        store_id: uuid.UUID,
        debt_transaction_id: uuid.UUID,
        amount: Decimal,
        method: str,
        status: str,
        reference: str | None,
        note: str | None,
    ) -> Payment:
        payment = Payment(
            store_id=store_id,
            debt_transaction_id=debt_transaction_id,
            amount=amount,
            method=method,
            status=status,
            reference=reference,
            note=note,
        )
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def list_transactions(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[Sequence[DebtTransaction], int]:
        query = (
            select(DebtTransaction)
            .options(selectinload(DebtTransaction.payments))
            .where(DebtTransaction.store_id == store_id, DebtTransaction.debtor_id == debtor_id)
        )
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(DebtTransaction.transaction_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
