from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Expense, ExpenseCategory


class ExpensesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_category(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> ExpenseCategory | None:
        result = await self.db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.id == category_id,
                ExpenseCategory.store_id == store_id,
                ExpenseCategory.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_category_by_name(
        self,
        *,
        store_id: uuid.UUID,
        name: str,
    ) -> ExpenseCategory | None:
        result = await self.db.execute(
            select(ExpenseCategory).where(
                ExpenseCategory.store_id == store_id,
                ExpenseCategory.name == name,
                ExpenseCategory.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_categories(self, *, store_id: uuid.UUID) -> Sequence[ExpenseCategory]:
        result = await self.db.execute(
            select(ExpenseCategory)
            .where(ExpenseCategory.store_id == store_id, ExpenseCategory.is_active.is_(True))
            .order_by(ExpenseCategory.name.asc())
        )
        return result.scalars().all()

    async def create_category(
        self,
        *,
        store_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> ExpenseCategory:
        category = ExpenseCategory(store_id=store_id, name=name, description=description)
        self.db.add(category)
        await self.db.flush()
        return category

    async def get_expense(self, *, store_id: uuid.UUID, expense_id: uuid.UUID) -> Expense | None:
        result = await self.db.execute(
            select(Expense).where(Expense.id == expense_id, Expense.store_id == store_id)
        )
        return result.scalar_one_or_none()

    def _expenses_query(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Select[tuple[Expense]]:
        query = select(Expense).where(Expense.store_id == store_id)
        if category_id is not None:
            query = query.where(Expense.category_id == category_id)
        if date_from is not None:
            query = query.where(Expense.spent_at >= date_from)
        if date_to is not None:
            query = query.where(Expense.spent_at <= date_to)
        return query

    async def list_expenses(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        limit: int,
    ) -> tuple[Sequence[Expense], int]:
        query = self._expenses_query(
            store_id=store_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
        )
        total = await self.count(query)
        result = await self.db.execute(
            query.order_by(Expense.spent_at.desc()).offset((page - 1) * limit).limit(limit)
        )
        return result.scalars().all(), total

    async def create_expense(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID | None,
        amount: Decimal,
        payment_method: str,
        note: str | None,
    ) -> Expense:
        expense = Expense(
            store_id=store_id,
            category_id=category_id,
            amount=amount,
            payment_method=payment_method,
            note=note,
        )
        self.db.add(expense)
        await self.db.flush()
        return expense

    async def count(self, query: Select) -> int:
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        result = await self.db.execute(count_query)
        return int(result.scalar_one())
