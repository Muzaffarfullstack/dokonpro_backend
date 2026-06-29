import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.enums import StockMovementType
from app.core.exceptions import AppException
from app.models import Category, Product, StockMovement, StoreProduct
from app.modules.products.schemas import (
    CategoryCreateRequest,
    ProductCatalogCreateRequest,
    StockMovementCreateRequest,
    StoreProductCreateRequest,
    StoreProductUpdateRequest,
)
from app.modules.products.service import ProductsService


class FakeDb:
    def __init__(self) -> None:
        self.committed = False
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: object, attribute_names: list[str] | None = None) -> None:
        self.refreshed.append(obj)


class FakeProductsRepository:
    categories_by_id: dict[uuid.UUID, Category] = {}
    categories_by_slug: dict[str, Category] = {}
    products_by_slug: dict[str, Product] = {}
    products_by_barcode: dict[str, Product] = {}
    products_by_id: dict[uuid.UUID, Product] = {}
    store_products_by_product: dict[tuple[uuid.UUID, uuid.UUID], StoreProduct] = {}
    store_products_by_sku: dict[tuple[uuid.UUID, str], StoreProduct] = {}
    store_products_by_id: dict[tuple[uuid.UUID, uuid.UUID], StoreProduct] = {}
    movements: list[StockMovement] = []

    def __init__(self, _: object) -> None:
        pass

    async def get_category_by_id(self, category_id: uuid.UUID) -> Category | None:
        return type(self).categories_by_id.get(category_id)

    async def get_category_by_slug(self, slug: str) -> Category | None:
        return type(self).categories_by_slug.get(slug)

    async def create_category(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
        description: str | None,
        display_order: int,
    ) -> Category:
        category = Category(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            parent_id=parent_id,
            description=description,
            display_order=display_order,
            is_active=True,
        )
        type(self).categories_by_id[category.id] = category
        type(self).categories_by_slug[slug] = category
        return category

    async def list_categories(self) -> list[Category]:
        return list(type(self).categories_by_slug.values())

    async def get_product_by_id(self, product_id: uuid.UUID) -> Product | None:
        return type(self).products_by_id.get(product_id)

    async def get_product_by_slug(self, slug: str) -> Product | None:
        return type(self).products_by_slug.get(slug)

    async def get_product_by_barcode(self, barcode: str) -> Product | None:
        return type(self).products_by_barcode.get(barcode)

    async def create_product(
        self,
        *,
        name: str,
        slug: str,
        category_id: uuid.UUID | None,
        barcode: str | None,
        description: str | None,
        unit: str,
        image_url: str | None,
    ) -> Product:
        product = Product(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            category_id=category_id,
            barcode=barcode,
            description=description,
            unit=unit,
            image_url=image_url,
            is_active=True,
        )
        type(self).products_by_slug[slug] = product
        type(self).products_by_id[product.id] = product
        if barcode:
            type(self).products_by_barcode[barcode] = product
        return product

    async def get_store_product_by_product_id(
        self,
        *,
        store_id: uuid.UUID,
        product_id: uuid.UUID,
    ) -> StoreProduct | None:
        return type(self).store_products_by_product.get((store_id, product_id))

    async def get_store_product_by_sku(
        self,
        *,
        store_id: uuid.UUID,
        local_sku: str,
    ) -> StoreProduct | None:
        return type(self).store_products_by_sku.get((store_id, local_sku))

    async def get_store_product_by_barcode(
        self,
        *,
        store_id: uuid.UUID,
        barcode: str,
    ) -> StoreProduct | None:
        for (current_store_id, _), store_product in type(self).store_products_by_id.items():
            if current_store_id == store_id and store_product.product.barcode == barcode:
                return store_product
        return None

    async def create_store_product(
        self,
        *,
        store_id: uuid.UUID,
        product_id: uuid.UUID,
        local_sku: str | None,
        cost_price: Decimal,
        sale_price: Decimal,
        stock_quantity: Decimal,
        low_stock_threshold: Decimal,
        expiry_date: date | None,
    ) -> StoreProduct:
        product = type(self).products_by_id[product_id]
        store_product = StoreProduct(
            id=uuid.uuid4(),
            store_id=store_id,
            product_id=product_id,
            local_sku=local_sku,
            cost_price=cost_price,
            sale_price=sale_price,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            expiry_date=expiry_date,
            is_active=True,
        )
        store_product.product = product
        type(self).store_products_by_product[(store_id, product_id)] = store_product
        type(self).store_products_by_id[(store_id, store_product.id)] = store_product
        if local_sku:
            type(self).store_products_by_sku[(store_id, local_sku)] = store_product
        return store_product

    async def get_store_product(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct | None:
        return type(self).store_products_by_id.get((store_id, store_product_id))

    async def get_store_product_for_update(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
    ) -> StoreProduct | None:
        return await self.get_store_product(store_id=store_id, store_product_id=store_product_id)

    async def list_catalog(
        self,
        *,
        search: str | None,
        page: int,
        limit: int,
    ) -> tuple[list[Product], int]:
        products = list(type(self).products_by_id.values())
        if search:
            products = [product for product in products if search.lower() in product.name.lower()]
        return products[(page - 1) * limit : page * limit], len(products)

    async def list_store_products(
        self,
        *,
        store_id: uuid.UUID,
        search: str | None,
        barcode: str | None,
        category_id: uuid.UUID | None,
        low_stock: bool | None,
        page: int,
        limit: int,
    ) -> tuple[list[StoreProduct], int]:
        products = [
            product
            for (current_store_id, _), product in type(self).store_products_by_id.items()
            if current_store_id == store_id
        ]
        if search:
            products = [
                product
                for product in products
                if search.lower() in product.product.name.lower()
            ]
        if barcode:
            products = [product for product in products if product.product.barcode == barcode]
        if category_id:
            products = [
                product for product in products if product.product.category_id == category_id
            ]
        if low_stock is True:
            products = [
                product
                for product in products
                if product.stock_quantity <= product.low_stock_threshold
            ]
        return products[(page - 1) * limit : page * limit], len(products)

    async def create_stock_movement(
        self,
        *,
        store_id: uuid.UUID,
        store_product_id: uuid.UUID,
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
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            reason=reason,
            note=note,
        )
        type(self).movements.append(movement)
        return movement


@pytest.fixture(autouse=True)
def patch_repository(monkeypatch):
    from app.modules.products import service as products_service

    FakeProductsRepository.categories_by_slug = {}
    FakeProductsRepository.categories_by_id = {}
    FakeProductsRepository.products_by_slug = {}
    FakeProductsRepository.products_by_barcode = {}
    FakeProductsRepository.products_by_id = {}
    FakeProductsRepository.store_products_by_product = {}
    FakeProductsRepository.store_products_by_sku = {}
    FakeProductsRepository.store_products_by_id = {}
    FakeProductsRepository.movements = []
    monkeypatch.setattr(products_service, "ProductsRepository", FakeProductsRepository)


@pytest.mark.asyncio
async def test_create_category_supports_parent_and_prevents_duplicates() -> None:
    service = ProductsService(FakeDb())
    parent = await service.create_category(CategoryCreateRequest(name="Ichimliklar"))

    child = await service.create_category(
        CategoryCreateRequest(name="Gazli ichimliklar", parent_id=parent.id)
    )

    assert child.parent_id == parent.id

    with pytest.raises(AppException) as exc:
        await service.create_category(CategoryCreateRequest(name="Ichimliklar"))

    assert exc.value.code == "CATEGORY_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_category_rejects_missing_parent() -> None:
    service = ProductsService(FakeDb())

    with pytest.raises(AppException) as exc:
        await service.create_category(
            CategoryCreateRequest(name="Gazli ichimliklar", parent_id=uuid.uuid4())
        )

    assert exc.value.code == "CATEGORY_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_catalog_product_prevents_global_duplicates() -> None:
    service = ProductsService(FakeDb())
    await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Shakar", barcode="123456", unit="kg")
    )

    with pytest.raises(AppException) as exc:
        await service.create_catalog_product(
            ProductCatalogCreateRequest(name="Shakar", barcode="999999", unit="kg")
        )

    assert exc.value.code == "PRODUCT_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_catalog_product_rejects_duplicate_barcode() -> None:
    service = ProductsService(FakeDb())
    await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Shakar", barcode="123456", unit="kg")
    )

    with pytest.raises(AppException) as exc:
        await service.create_catalog_product(
            ProductCatalogCreateRequest(name="Un", barcode="123456", unit="kg")
        )

    assert exc.value.code == "BARCODE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_catalog_product_rejects_missing_category() -> None:
    service = ProductsService(FakeDb())

    with pytest.raises(AppException) as exc:
        await service.create_catalog_product(
            ProductCatalogCreateRequest(name="Shakar", category_id=uuid.uuid4(), unit="kg")
        )

    assert exc.value.code == "CATEGORY_NOT_FOUND"


@pytest.mark.asyncio
async def test_add_product_to_store_creates_initial_stock_movement() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Shakar", barcode="123456", unit="kg")
    )
    store_id = uuid.uuid4()

    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=product.id,
            local_sku="S-1",
            cost_price=Decimal("9000"),
            sale_price=Decimal("11000"),
            stock_quantity=Decimal("20"),
            low_stock_threshold=Decimal("5"),
            expiry_date=date(2026, 12, 31),
        ),
    )

    assert store_product.product_id == product.id
    assert store_product.expiry_date == date(2026, 12, 31)
    assert FakeProductsRepository.movements[0].movement_type == StockMovementType.IN.value
    assert FakeProductsRepository.movements[0].quantity == Decimal("20")


@pytest.mark.asyncio
async def test_add_product_to_store_rejects_missing_global_product() -> None:
    service = ProductsService(FakeDb())

    with pytest.raises(AppException) as exc:
        await service.add_product_to_store(
            store_id=uuid.uuid4(),
            payload=StoreProductCreateRequest(
                product_id=uuid.uuid4(),
                sale_price=Decimal("11000"),
            ),
        )

    assert exc.value.code == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_add_product_to_store_prevents_duplicate_store_product() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Un", unit="kg")
    )
    store_id = uuid.uuid4()
    payload = StoreProductCreateRequest(product_id=product.id, sale_price=Decimal("8000"))

    await service.add_product_to_store(store_id=store_id, payload=payload)
    with pytest.raises(AppException) as exc:
        await service.add_product_to_store(store_id=store_id, payload=payload)

    assert exc.value.code == "STORE_PRODUCT_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_add_product_to_store_prevents_duplicate_local_sku() -> None:
    service = ProductsService(FakeDb())
    first_product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Un"))
    second_product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Tuz"))
    store_id = uuid.uuid4()

    await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=first_product.id,
            local_sku="SKU-1",
            sale_price=Decimal("8000"),
        ),
    )

    with pytest.raises(AppException) as exc:
        await service.add_product_to_store(
            store_id=store_id,
            payload=StoreProductCreateRequest(
                product_id=second_product.id,
                local_sku="SKU-1",
                sale_price=Decimal("3000"),
            ),
        )

    assert exc.value.code == "LOCAL_SKU_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_store_product_changes_prices_and_expiry_date() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Sut"))
    store_id = uuid.uuid4()
    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=product.id,
            local_sku="SUT-1",
            sale_price=Decimal("9000"),
        ),
    )

    updated = await service.update_store_product(
        store_id=store_id,
        store_product_id=store_product.id,
        payload=StoreProductUpdateRequest(
            local_sku="SUT-2",
            cost_price=Decimal("7000"),
            sale_price=Decimal("9500"),
            low_stock_threshold=Decimal("3"),
            expiry_date=date(2026, 9, 1),
        ),
    )

    assert updated.local_sku == "SUT-2"
    assert updated.cost_price == Decimal("7000")
    assert updated.sale_price == Decimal("9500")
    assert updated.low_stock_threshold == Decimal("3")
    assert updated.expiry_date == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_update_store_product_prevents_duplicate_local_sku() -> None:
    service = ProductsService(FakeDb())
    first_product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Sut"))
    second_product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Qatiq"))
    store_id = uuid.uuid4()
    await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=first_product.id,
            local_sku="SKU-1",
            sale_price=Decimal("9000"),
        ),
    )
    second_store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=second_product.id,
            local_sku="SKU-2",
            sale_price=Decimal("10000"),
        ),
    )

    with pytest.raises(AppException) as exc:
        await service.update_store_product(
            store_id=store_id,
            store_product_id=second_store_product.id,
            payload=StoreProductUpdateRequest(local_sku="SKU-1"),
        )

    assert exc.value.code == "LOCAL_SKU_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_deactivate_store_product_marks_item_inactive() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Makaron"))
    store_id = uuid.uuid4()
    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(product_id=product.id, sale_price=Decimal("12000")),
    )

    await service.deactivate_store_product(
        store_id=store_id,
        store_product_id=store_product.id,
    )

    assert store_product.is_active is False


@pytest.mark.asyncio
async def test_get_store_product_by_barcode_is_store_scoped() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Shakar", barcode="123456")
    )
    store_id = uuid.uuid4()
    other_store_id = uuid.uuid4()
    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(product_id=product.id, sale_price=Decimal("11000")),
    )

    found = await service.get_store_product_by_barcode(store_id=store_id, barcode="123456")

    assert found.id == store_product.id
    with pytest.raises(AppException) as exc:
        await service.get_store_product_by_barcode(store_id=other_store_id, barcode="123456")

    assert exc.value.code == "STORE_PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_catalog_and_store_products_return_pagination() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Shakar"))
    store_id = uuid.uuid4()
    await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(product_id=product.id, sale_price=Decimal("11000")),
    )

    catalog = await service.list_catalog(search="Sha", page=1, limit=10)
    inventory = await service.list_store_products(
        store_id=store_id,
        search="Sha",
        barcode=None,
        category_id=None,
        low_stock=None,
        page=1,
        limit=10,
    )

    assert catalog.pagination.total == 1
    assert inventory.pagination.total == 1
    assert inventory.data[0].product.name == "Shakar"


@pytest.mark.asyncio
async def test_list_store_products_supports_barcode_category_and_low_stock_filters() -> None:
    service = ProductsService(FakeDb())
    category = await service.create_category(CategoryCreateRequest(name="Ichimliklar"))
    product = await service.create_catalog_product(
        ProductCatalogCreateRequest(name="Cola", barcode="478001", category_id=category.id)
    )
    store_id = uuid.uuid4()
    await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=product.id,
            sale_price=Decimal("9000"),
            stock_quantity=Decimal("2"),
            low_stock_threshold=Decimal("3"),
        ),
    )

    result = await service.list_store_products(
        store_id=store_id,
        search=None,
        barcode="478001",
        category_id=category.id,
        low_stock=True,
        page=1,
        limit=10,
    )

    assert result.pagination.total == 1
    assert result.data[0].product.name == "Cola"


@pytest.mark.asyncio
async def test_stock_out_decreases_inventory_and_blocks_negative_stock() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Guruch"))
    store_id = uuid.uuid4()
    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=product.id,
            sale_price=Decimal("15000"),
            stock_quantity=Decimal("10"),
        ),
    )

    await service.record_stock_movement(
        store_id=store_id,
        store_product_id=store_product.id,
        payload=StockMovementCreateRequest(
            movement_type=StockMovementType.OUT,
            quantity=Decimal("3"),
        ),
    )
    assert store_product.stock_quantity == Decimal("7")

    with pytest.raises(AppException) as exc:
        await service.record_stock_movement(
            store_id=store_id,
            store_product_id=store_product.id,
            payload=StockMovementCreateRequest(
                movement_type=StockMovementType.OUT,
                quantity=Decimal("8"),
            ),
        )
    assert exc.value.code == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_stock_adjustment_sets_absolute_inventory_quantity() -> None:
    service = ProductsService(FakeDb())
    product = await service.create_catalog_product(ProductCatalogCreateRequest(name="Tuz"))
    store_id = uuid.uuid4()
    store_product = await service.add_product_to_store(
        store_id=store_id,
        payload=StoreProductCreateRequest(
            product_id=product.id,
            sale_price=Decimal("3000"),
            stock_quantity=Decimal("10"),
        ),
    )

    movement = await service.record_stock_movement(
        store_id=store_id,
        store_product_id=store_product.id,
        payload=StockMovementCreateRequest(
            movement_type=StockMovementType.ADJUSTMENT,
            quantity=Decimal("4"),
        ),
    )

    assert store_product.stock_quantity == Decimal("4")
    assert movement.quantity == Decimal("-6")
