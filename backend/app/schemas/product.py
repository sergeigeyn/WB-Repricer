"""Product schemas."""

from datetime import datetime

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int
    nm_id: int
    vendor_code: str | None
    brand: str | None
    category: str | None
    title: str | None
    image_url: str | None
    cost_price: float | None
    tax_rate: float | None
    total_stock: int = 0
    is_active: bool
    is_locomotive: bool
    created_at: datetime
    # Price data (from latest snapshot)
    current_price: float | None = None
    discount_pct: float | None = None
    final_price: float | None = None

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    items: list[ProductResponse]
    total: int


class ProductCostUpdate(BaseModel):
    cost_price: float | None = None
    tax_rate: float | None = None
    extra_costs_json: str | None = None
