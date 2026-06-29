from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.responses import ApiListResponse
from app.models import Expense, ExpenseCategory
from app.modules.expenses.repository import ExpensesRepository
from app.modules.expenses.schemas import (
    ExpenseCategoryCreateRequest,
    ExpenseCategoryUpdateRequest,
    ExpenseCreateRequest,
    ExpenseUpdateRequest,
)
from app.utils.pagination import build_pagination


class ExpensesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ExpensesRepository(db)

    async def list_categories(self, *, store_id: uuid.UUID) -> list[ExpenseCategory]:
        return list(await self.repo.list_categories(store_id=store_id))

    async def create_category(
        self,
        *,
        store_id: uuid.UUID,
        payload: ExpenseCategoryCreateRequest,
    ) -> ExpenseCategory:
        await self._ensure_unique_category_name(store_id=store_id, name=payload.name)
        category = await self.repo.create_category(
            store_id=store_id,
            name=payload.name,
            description=payload.description,
        )
        await self.db.commit()
        return category

    async def update_category(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
        payload: ExpenseCategoryUpdateRequest,
    ) -> ExpenseCategory:
        category = await self._get_category(store_id=store_id, category_id=category_id)
        if payload.name is not None and payload.name != category.name:
            await self._ensure_unique_category_name(store_id=store_id, name=payload.name)
            category.name = payload.name
        if payload.description is not None:
            category.description = payload.description
        await self.db.commit()
        return category

    async def deactivate_category(self, *, store_id: uuid.UUID, category_id: uuid.UUID) -> None:
        category = await self._get_category(store_id=store_id, category_id=category_id)
        category.is_active = False
        await self.db.commit()

    async def list_expenses(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        limit: int,
    ) -> ApiListResponse[Expense]:
        if category_id is not None:
            await self._get_category(store_id=store_id, category_id=category_id)
        expenses, total = await self.repo.list_expenses(
            store_id=store_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        )
        return ApiListResponse(
            data=list(expenses),
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    async def create_expense(
        self,
        *,
        store_id: uuid.UUID,
        payload: ExpenseCreateRequest,
    ) -> Expense:
        if payload.category_id is not None:
            await self._get_category(store_id=store_id, category_id=payload.category_id)
        expense = await self.repo.create_expense(
            store_id=store_id,
            category_id=payload.category_id,
            amount=payload.amount,
            payment_method=payload.payment_method.value,
            note=payload.note,
        )
        await self.db.commit()
        return expense

    async def get_expense(self, *, store_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
        expense = await self.repo.get_expense(store_id=store_id, expense_id=expense_id)
        if expense is None:
            raise AppException(
                code="EXPENSE_NOT_FOUND", message="Xarajat topilmadi.", status_code=404
            )
        return expense

    async def update_expense(
        self,
        *,
        store_id: uuid.UUID,
        expense_id: uuid.UUID,
        payload: ExpenseUpdateRequest,
    ) -> Expense:
        expense = await self.get_expense(store_id=store_id, expense_id=expense_id)
        if payload.category_id is not None:
            await self._get_category(store_id=store_id, category_id=payload.category_id)
            expense.category_id = payload.category_id
        if payload.amount is not None:
            expense.amount = payload.amount
        if payload.payment_method is not None:
            expense.payment_method = payload.payment_method.value
        if payload.note is not None:
            expense.note = payload.note
        await self.db.commit()
        return expense

    async def delete_expense(self, *, store_id: uuid.UUID, expense_id: uuid.UUID) -> None:
        expense = await self.get_expense(store_id=store_id, expense_id=expense_id)
        await self.db.delete(expense)
        await self.db.commit()

    async def _get_category(
        self,
        *,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> ExpenseCategory:
        category = await self.repo.get_category(store_id=store_id, category_id=category_id)
        if category is None:
            raise AppException(
                code="EXPENSE_CATEGORY_NOT_FOUND",
                message="Xarajat kategoriyasi topilmadi.",
                status_code=404,
                field="category_id",
            )
        return category

    async def _ensure_unique_category_name(self, *, store_id: uuid.UUID, name: str) -> None:
        if await self.repo.get_category_by_name(store_id=store_id, name=name):
            raise AppException(
                code="EXPENSE_CATEGORY_ALREADY_EXISTS",
                message="Bu nom bilan xarajat kategoriyasi mavjud.",
                status_code=409,
                field="name",
            )
