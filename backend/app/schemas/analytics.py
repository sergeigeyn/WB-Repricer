"""General analytics page schemas."""

from datetime import date

from pydantic import BaseModel


class DailyTrend(BaseModel):
    """Daily aggregated data across all products."""

    date: date
    orders: int = 0
    revenue: float = 0
    profit: float = 0


class DailyFunnel(BaseModel):
    """Daily funnel aggregated across all products."""

    date: date
    views: int = 0
    cart: int = 0
    orders: int = 0
    buyouts: int = 0
    cart_conversion: float | None = None
    order_conversion: float | None = None
    buyout_pct: float | None = None


class TopProduct(BaseModel):
    """Product ranked by orders."""

    product_id: int
    nm_id: int
    title: str | None = None
    image_url: str | None = None
    orders: int = 0
    revenue: float = 0
    share_pct: float = 0


class WeekdayAvg(BaseModel):
    """Average orders/revenue by weekday."""

    weekday: int
    weekday_name: str
    avg_orders: float = 0
    avg_revenue: float = 0


class TotalsSummary(BaseModel):
    """Period totals."""

    orders: int = 0
    revenue: float = 0
    profit: float = 0
    avg_check: float = 0
    views: int = 0
    cart: int = 0
    avg_cart_conversion: float | None = None
    avg_order_conversion: float | None = None
    avg_buyout_pct: float | None = None


class AnalyticsOverviewResponse(BaseModel):
    """Full analytics overview response."""

    daily_trend: list[DailyTrend] = []
    daily_funnel: list[DailyFunnel] = []
    top_products: list[TopProduct] = []
    weekday_avg: list[WeekdayAvg] = []
    totals: TotalsSummary
    period: str
    account_id: int | None = None
