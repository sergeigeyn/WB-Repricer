"""Dashboard schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class DashboardKPI(BaseModel):
    """Top-row KPI cards."""

    total_orders: int = 0
    total_revenue: float = 0
    total_profit: float = 0
    avg_margin_pct: float | None = None

    # Change vs previous period
    orders_change_pct: float | None = None
    revenue_change_pct: float | None = None
    profit_change_pct: float | None = None

    # Operational
    active_products: int = 0
    total_products: int = 0
    total_stock: int = 0
    price_changes_today: int = 0


class DashboardAlert(BaseModel):
    """Problem product alert."""

    type: str  # "negative_margin" | "low_margin" | "no_cost" | "no_strategy"
    severity: str  # "critical" | "warning" | "info"
    product_id: int
    nm_id: int
    title: str | None = None
    image_url: str | None = None
    value: float | None = None
    detail: str | None = None


class DashboardPromotion(BaseModel):
    """Active/upcoming promotion card."""

    id: int
    name: str
    status: str
    start_date: date | None = None
    end_date: date | None = None
    in_action_count: int = 0
    total_available: int = 0
    avg_promo_margin: float | None = None
    profitable_count: int = 0


class DashboardTopProduct(BaseModel):
    """Top product by orders."""

    product_id: int
    nm_id: int
    title: str | None = None
    image_url: str | None = None
    orders: int = 0
    revenue: float = 0
    margin_pct: float | None = None
    margin_rub: float | None = None


class DashboardResponse(BaseModel):
    """Full dashboard response."""

    kpi: DashboardKPI
    alerts: list[DashboardAlert] = []
    active_promotions: list[DashboardPromotion] = []
    top_products: list[DashboardTopProduct] = []
    products_without_strategy: int = 0
    products_without_cost: int = 0
    period: str = "7d"
    account_id: int | None = None
