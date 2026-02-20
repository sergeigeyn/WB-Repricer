"""Promotion schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class PromotionResponse(BaseModel):
    id: int
    wb_promo_id: str | None
    name: str
    start_date: date | None = None
    end_date: date | None = None
    promo_type: str | None = None
    status: str | None = None
    in_action_count: int = 0
    total_available: int = 0
    # Aggregated from promotion_products
    products_count: int = 0
    avg_current_margin: float | None = None
    avg_promo_margin: float | None = None
    profitable_count: int = 0

    model_config = {"from_attributes": True}


class PromotionListResponse(BaseModel):
    items: list[PromotionResponse]
    total: int


class PromotionProductResponse(BaseModel):
    nm_id: int
    vendor_code: str | None = None
    title: str | None = None
    image_url: str | None = None
    plan_price: float | None = None
    plan_discount: float | None = None
    current_price: float | None = None
    in_action: bool = False
    current_margin_pct: float | None = None
    current_margin_rub: float | None = None
    promo_margin_pct: float | None = None
    promo_margin_rub: float | None = None
    decision: str = "pending"

    model_config = {"from_attributes": True}


class PromotionDetailResponse(BaseModel):
    promotion: PromotionResponse
    products: list[PromotionProductResponse]


class DecisionUpdate(BaseModel):
    nm_ids: list[int]
    decision: str  # "enter" | "skip"
