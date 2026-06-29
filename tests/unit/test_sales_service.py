import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.enums import PaymentMethod, SalePaymentStatus, SaleStatus, StockMovementType
from app.core.exceptions import AppException
from app.models import Payment, Product, Sale, SaleItem, StockMovement, StoreProduct
from app.modules.sales.schemas import SaleCheckoutItemRequest, SaleCheckoutRequest
from app.modules.sales.service import SalesService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeSalesRepository:
    store_products: dict[tuple[uuid.UUID, uuid.UUID], StoreProduct] = {}
    sales: dict[tuple[uuid.UUID, uuid.UUID], Sale] = {}
    sale_items: list[SaleItem] = []
    payments: list[Payment] = []
    movements: list[StockMovement] = []

    def __init__(self, _: object) -> None:
        pass

    async def get_store_product_for_update(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct | None:
        return type(self).store_products.get((store_id, store_product_id))

    async def create_sale(
        self,
        *,
        store_id: uuid.UUID,
        customer_name: str | None,
        customer_phone: str | None,
        status: str,
        payment_status: str,
        subtotal: Decimal,
        discount_total: Decimal,
        total_amount: Decimal,
        paid_amount: Decimal,
        change_amount: Decimal,
        note: str | None,
    ) -> Sale:
        sale = Sale(
            id=uuid.uuid4(),
            store_id=store_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            status=status,
            payment_status=payment_status,
            subtotal=subtotal,
            discount_total=discount_total,
            total_amount=total_amount,
            paid_amount=paid_amount,
            change_amount=change_amount,
            note=note,
            sold_at=datetime.now(UTC),
        )
        sale.items = []
        sale.payments = []
        type(self).sales[(store_id, sale.id)] = sale
        return sale

    async def create_sale_item(
        self,
        *,
        store_id: uuid.UUID,
        sale_id: uuid.UUID,
        store_product_id: uuid.UUID,
        product_name: str,
        local_sku: str | None,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        total_amount: Decimal,
    ) -> SaleItem:
        item = SaleItem(
            id=uuid.uuid4(),
            store_id=store_id,
            sale_id=sale_id,
            store_product_id=store_product_id,
            product_name=product_name,
            local_sku=local_sku,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            total_amount=total_amount,
        )
        type(self).sale_items.append(item)
        type(self).sales[(store_id, sale_id)].items.append(item)
        return item

    async def create_payment(
        self,
        *,
        store_id: uuid.UUID,
        sale_id: uuid.UUID,
        amount: Decimal,
        method: str,
        status: str,
        reference: str | None,
        note: str | None,
    ) -> Payment:
        payment = Payment(
            id=uuid.uuid4(),
            store_id=store_id,
            sale_id=sale_id,
            amount=amount,
            method=method,
            status=status,
            reference=reference,
            note=note,
            paid_at=datetime.now(UTC),
        )
        type(self).payments.append(payment)
        type(self).sales[(store_id, sale_id)].payments.append(payment)
        return payment

    async def create_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
        sale_id: uuid.UUID,
        movement_type: str,
        quantity: Decimal,
        unit_cost: Decimal,
        reason: str | None,
        note: str | None,
    ) -> StockMovement:
        movement = StockMovement(
            id=uuid.uuid4(),
            store_id=store_id,
            store_product_id=store_product_id,
            sale_id=sale_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reason=reason,
            note=note,
        )
        type(self).movements.append(movement)
        return movement

    async def get_sale(self, *, store_id: uuid.UUID, sale_id: uuid.UUID) -> Sale | None:
        return type(self).sales.get((store_id, sale_id))

    async def list_sales(
        self,
        *,
        store_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> tuple[list[Sale], int]:
        sales = [
            sale
            for (current_store_id, _), sale in type(self).sales.items()
            if current_store_id == store_id
        ]
        return sales[(page - 1) * limit : page * limit], len(sales)


@pytest.fixture(autouse=True)
def patch_repository(monkeypatch):
    from app.modules.sales import service as sales_service

    FakeSalesRepository.store_products = {}
    FakeSalesRepository.sales = {}
    FakeSalesRepository.sale_items = []
    FakeSalesRepository.payments = []
    FakeSalesRepository.movements = []
    monkeypatch.setattr(sales_service, "SalesRepository", FakeSalesRepository)


def make_store_product(
    *,
    store_id: uuid.UUID,
    name: str = "Shakar",
    stock: Decimal = Decimal("10"),
    sale_price: Decimal = Decimal("11000"),
    cost_price: Decimal = Decimal("9000"),
) -> StoreProduct:
    product = Product(id=uuid.uuid4(), name=name, slug=name.lower(), unit="kg", is_active=True)
    store_product = StoreProduct(
        id=uuid.uuid4(),
        store_id=store_id,
        product_id=product.id,
        local_sku="SKU-1",
        cost_price=cost_price,
        sale_price=sale_price,
        stock_quantity=stock,
        low_stock_threshold=Decimal("1"),
        is_active=True,
    )
    store_product.product = product
    FakeSalesRepository.store_products[(store_id, store_product.id)] = store_product
    return store_product


@pytest.mark.asyncio
async def test_checkout_creates_sale_items_payment_and_stock_movement() -> None:
    db = FakeDb()
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id)

    sale = await SalesService(db).checkout(
        store_id=store_id,
        payload=SaleCheckoutRequest(
            customer_name="Ali",
            items=[
                SaleCheckoutItemRequest(
                    store_product_id=store_product.id,
                    quantity=Decimal("2"),
                    discount_amount=Decimal("1000"),
                )
            ],
            discount_amount=Decimal("500"),
            paid_amount=Decimal("25000"),
            payment_method=PaymentMethod.CASH,
        ),
    )

    assert db.committed is True
    assert sale.status == SaleStatus.COMPLETED.value
    assert sale.payment_status == SalePaymentStatus.PAID.value
    assert sale.subtotal == Decimal("22000.00")
    assert sale.discount_total == Decimal("1500.00")
    assert sale.total_amount == Decimal("20500.00")
    assert sale.paid_amount == Decimal("20500.00")
    assert sale.change_amount == Decimal("4500.00")
    assert store_product.stock_quantity == Decimal("8")
    assert sale.items[0].product_name == "Shakar"
    assert sale.items[0].total_amount == Decimal("21000.00")
    assert sale.payments[0].amount == Decimal("20500.00")
    assert FakeSalesRepository.movements[0].movement_type == StockMovementType.OUT.value
    assert FakeSalesRepository.movements[0].quantity == Decimal("-2")


@pytest.mark.asyncio
async def test_checkout_sets_partial_payment_status() -> None:
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id)

    sale = await SalesService(FakeDb()).checkout(
        store_id=store_id,
        payload=SaleCheckoutRequest(
            items=[
                SaleCheckoutItemRequest(
                    store_product_id=store_product.id,
                    quantity=Decimal("1"),
                )
            ],
            paid_amount=Decimal("5000"),
        ),
    )

    assert sale.payment_status == SalePaymentStatus.PARTIAL.value
    assert sale.paid_amount == Decimal("5000.00")
    assert sale.change_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_checkout_rejects_duplicate_items() -> None:
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id)

    with pytest.raises(AppException) as exc:
        await SalesService(FakeDb()).checkout(
            store_id=store_id,
            payload=SaleCheckoutRequest(
                items=[
                    SaleCheckoutItemRequest(
                        store_product_id=store_product.id,
                        quantity=Decimal("1"),
                    ),
                    SaleCheckoutItemRequest(
                        store_product_id=store_product.id,
                        quantity=Decimal("1"),
                    ),
                ],
            ),
        )

    assert exc.value.code == "DUPLICATE_SALE_ITEM"


@pytest.mark.asyncio
async def test_checkout_rejects_insufficient_stock() -> None:
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id, stock=Decimal("1"))

    with pytest.raises(AppException) as exc:
        await SalesService(FakeDb()).checkout(
            store_id=store_id,
            payload=SaleCheckoutRequest(
                items=[
                    SaleCheckoutItemRequest(
                        store_product_id=store_product.id,
                        quantity=Decimal("2"),
                    )
                ],
            ),
        )

    assert exc.value.code == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_checkout_rejects_discount_larger_than_item_total() -> None:
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id)

    with pytest.raises(AppException) as exc:
        await SalesService(FakeDb()).checkout(
            store_id=store_id,
            payload=SaleCheckoutRequest(
                items=[
                    SaleCheckoutItemRequest(
                        store_product_id=store_product.id,
                        quantity=Decimal("1"),
                        discount_amount=Decimal("12000"),
                    )
                ],
            ),
        )

    assert exc.value.code == "INVALID_DISCOUNT"


@pytest.mark.asyncio
async def test_list_and_get_sales() -> None:
    store_id = uuid.uuid4()
    store_product = make_store_product(store_id=store_id)
    service = SalesService(FakeDb())
    sale = await service.checkout(
        store_id=store_id,
        payload=SaleCheckoutRequest(
            items=[
                SaleCheckoutItemRequest(
                    store_product_id=store_product.id,
                    quantity=Decimal("1"),
                )
            ],
        ),
    )

    found = await service.get_sale(store_id=store_id, sale_id=sale.id)
    result = await service.list_sales(store_id=store_id, page=1, limit=10)

    assert found.id == sale.id
    assert result.pagination.total == 1
    assert result.data[0].id == sale.id
