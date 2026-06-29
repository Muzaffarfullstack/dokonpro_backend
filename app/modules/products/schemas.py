from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import StockMovementType


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    display_order: int = Field(default=0, ge=0)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    display_order: int


class ProductCatalogCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    category_id: uuid.UUID | None = None
    barcode: str | None = Field(default=None, min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    unit: str = Field(default="pcs", min_length=1, max_length=24)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", "barcode", "description", "unit", "image_url")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class ProductCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID | None
    name: str
    slug: str
    barcode: str | None
    description: str | None
    unit: str
    image_url: str | None


class StoreProductCreateRequest(BaseModel):
    product_id: uuid.UUID
    local_sku: str | None = Field(default=None, max_length=80)
    cost_price: Decimal = Field(default=Decimal("0"), ge=0)
    sale_price: Decimal = Field(ge=0)
    stock_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    low_stock_threshold: Decimal = Field(default=Decimal("0"), ge=0)
    expiry_date: date | None = None

    @field_validator("local_sku")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class StoreProductUpdateRequest(BaseModel):
    local_sku: str | None = Field(default=None, max_length=80)
    cost_price: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    expiry_date: date | None = None

    @field_validator("local_sku")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class ProductSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    barcode: str | None
    unit: str
    image_url: str | None


class StoreProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID
    local_sku: str | None
    cost_price: Decimal
    sale_price: Decimal
    stock_quantity: Decimal
    low_stock_threshold: Decimal
    expiry_date: date | None
    is_active: bool
    product: ProductSummaryResponse


class StockMovementCreateRequest(BaseModel):
    movement_type: StockMovementType
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    reason: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("reason", "note")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    store_product_id: uuid.UUID
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    reason: str | None
    note: str | None
    moved_at: datetime
