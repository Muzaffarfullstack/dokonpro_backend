import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.enums import DebtTransactionType, PaymentMethod, PaymentStatus
from app.core.exceptions import AppException
from app.models import Debtor, DebtTransaction, Payment, Sale
from app.modules.debts.schemas import (
    DebtAdjustmentRequest,
    DebtBorrowRequest,
    DebtorCreateRequest,
    DebtRepaymentRequest,
)
from app.modules.debts.service import DebtsService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeDebtsRepository:
    debtors: dict[tuple[uuid.UUID, uuid.UUID], Debtor] = {}
    phones: dict[tuple[uuid.UUID, str], Debtor] = {}
    transactions: list[DebtTransaction] = []
    payments: list[Payment] = []
    sales: dict[tuple[uuid.UUID, uuid.UUID], Sale] = {}

    def __init__(self, _: object) -> None:
        pass

    async def get_debtor_by_phone(self, *, store_id: uuid.UUID, phone: str) -> Debtor | None:
        return type(self).phones.get((store_id, phone))

    async def get_debtor(self, *, store_id: uuid.UUID, debtor_id: uuid.UUID) -> Debtor | None:
        return type(self).debtors.get((store_id, debtor_id))

    async def get_debtor_for_update(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
    ) -> Debtor | None:
        return type(self).debtors.get((store_id, debtor_id))

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
            id=uuid.uuid4(),
            store_id=store_id,
            name=name,
            phone=phone,
            address=address,
            note=note,
            balance=Decimal("0"),
            is_active=True,
        )
        debtor.transactions = []
        type(self).debtors[(store_id, debtor.id)] = debtor
        type(self).phones[(store_id, phone)] = debtor
        return debtor

    async def list_debtors(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[list[Debtor], int]:
        debtors = [
            debtor
            for (current_store_id, _), debtor in type(self).debtors.items()
            if current_store_id == store_id and debtor.is_active
        ]
        if search:
            debtors = [debtor for debtor in debtors if search.lower() in debtor.name.lower()]
        return debtors[(page - 1) * limit : page * limit], len(debtors)

    async def get_sale(self, *, store_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
        return type(self).sales.get((store_id, sale_id))

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
            id=uuid.uuid4(),
            store_id=store_id,
            debtor_id=debtor_id,
            transaction_type=transaction_type,
            amount=amount,
            sale_id=sale_id,
            note=note,
            transaction_at=datetime.now(UTC),
        )
        transaction.payments = []
        type(self).transactions.append(transaction)
        type(self).debtors[(store_id, debtor_id)].transactions.append(transaction)
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
            id=uuid.uuid4(),
            store_id=store_id,
            debt_transaction_id=debt_transaction_id,
            amount=amount,
            method=method,
            status=status,
            reference=reference,
            note=note,
            paid_at=datetime.now(UTC),
        )
        type(self).payments.append(payment)
        return payment

    async def list_transactions(
        self,
        *,
        store_id: uuid.UUID,
        debtor_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[list[DebtTransaction], int]:
        transactions = [
            transaction
            for transaction in type(self).transactions
            if transaction.store_id == store_id and transaction.debtor_id == debtor_id
        ]
        return transactions[(page - 1) * limit : page * limit], len(transactions)


@pytest.fixture(autouse=True)
def patch_repository(monkeypatch):
    from app.modules.debts import service as debts_service

    FakeDebtsRepository.debtors = {}
    FakeDebtsRepository.phones = {}
    FakeDebtsRepository.transactions = []
    FakeDebtsRepository.payments = []
    FakeDebtsRepository.sales = {}
    monkeypatch.setattr(debts_service, "DebtsRepository", FakeDebtsRepository)


async def create_debtor(service: DebtsService, store_id: uuid.UUID) -> Debtor:
    return await service.create_debtor(
        store_id=store_id,
        payload=DebtorCreateRequest(name="Ali", phone="+998901234567"),
    )


@pytest.mark.asyncio
async def test_create_debtor_normalizes_phone_and_blocks_duplicates() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()

    debtor = await create_debtor(service, store_id)

    assert debtor.phone == "+998901234567"
    with pytest.raises(AppException) as exc:
        await service.create_debtor(
            store_id=store_id,
            payload=DebtorCreateRequest(name="Vali", phone="+998 90 123 45 67"),
        )
    assert exc.value.code == "DEBTOR_PHONE_EXISTS"


@pytest.mark.asyncio
async def test_borrow_increases_balance_and_records_transaction() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)

    transaction = await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("100000"), note="Nasiya savdo"),
    )

    assert debtor.balance == Decimal("100000.00")
    assert transaction.transaction_type == DebtTransactionType.BORROW.value
    assert transaction.amount == Decimal("100000.00")


@pytest.mark.asyncio
async def test_borrow_rejects_missing_sale_link() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)

    with pytest.raises(AppException) as exc:
        await service.borrow(
            store_id=store_id,
            debtor_id=debtor.id,
            payload=DebtBorrowRequest(amount=Decimal("1000"), sale_id=uuid.uuid4()),
        )

    assert exc.value.code == "SALE_NOT_FOUND"


@pytest.mark.asyncio
async def test_repay_decreases_balance_and_creates_payment() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)
    await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("100000")),
    )

    transaction = await service.repay(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtRepaymentRequest(
            amount=Decimal("40000"),
            method=PaymentMethod.CARD,
            reference="CARD-1",
        ),
    )

    assert debtor.balance == Decimal("60000.00")
    assert transaction.transaction_type == DebtTransactionType.REPAYMENT.value
    assert transaction.payments[0].amount == Decimal("40000.00")
    assert transaction.payments[0].method == PaymentMethod.CARD.value
    assert transaction.payments[0].status == PaymentStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_repay_rejects_overpayment() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)
    await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("1000")),
    )

    with pytest.raises(AppException) as exc:
        await service.repay(
            store_id=store_id,
            debtor_id=debtor.id,
            payload=DebtRepaymentRequest(amount=Decimal("2000")),
        )

    assert exc.value.code == "PAYMENT_EXCEEDS_BALANCE"


@pytest.mark.asyncio
async def test_adjust_sets_absolute_balance_and_rejects_unchanged_balance() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)
    await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("100000")),
    )

    transaction = await service.adjust(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtAdjustmentRequest(new_balance=Decimal("75000")),
    )

    assert debtor.balance == Decimal("75000.00")
    assert transaction.transaction_type == DebtTransactionType.ADJUSTMENT.value
    assert transaction.amount == Decimal("25000.00")

    with pytest.raises(AppException) as exc:
        await service.adjust(
            store_id=store_id,
            debtor_id=debtor.id,
            payload=DebtAdjustmentRequest(new_balance=Decimal("75000")),
        )
    assert exc.value.code == "BALANCE_UNCHANGED"


@pytest.mark.asyncio
async def test_deactivate_debtor_requires_zero_balance() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)
    await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("1000")),
    )

    with pytest.raises(AppException) as exc:
        await service.deactivate_debtor(store_id=store_id, debtor_id=debtor.id)
    assert exc.value.code == "DEBTOR_HAS_BALANCE"

    await service.repay(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtRepaymentRequest(amount=Decimal("1000")),
    )
    await service.deactivate_debtor(store_id=store_id, debtor_id=debtor.id)
    assert debtor.is_active is False


@pytest.mark.asyncio
async def test_list_debtors_and_transactions_return_pagination() -> None:
    service = DebtsService(FakeDb())
    store_id = uuid.uuid4()
    debtor = await create_debtor(service, store_id)
    await service.borrow(
        store_id=store_id,
        debtor_id=debtor.id,
        payload=DebtBorrowRequest(amount=Decimal("1000")),
    )

    debtors = await service.list_debtors(store_id=store_id, search="Ali", page=1, limit=10)
    transactions = await service.list_transactions(
        store_id=store_id,
        debtor_id=debtor.id,
        page=1,
        limit=10,
    )

    assert debtors.pagination.total == 1
    assert transactions.pagination.total == 1
    assert transactions.data[0].transaction_type == DebtTransactionType.BORROW.value
