"""Product analytics schemas."""

from datetime import date

from pydantic import BaseModel


class DailyDataPoint(BaseModel):
    """Daily orders + price data for main chart."""

    date: date
    orders: int = 0
    returns: int = 0
    net_orders: int = 0
    price: float | None = None
    spp_price: float | None = None


class PricePoint(BaseModel):
    """Price snapshot per day."""

    date: date
    final_price: float
    spp_pct: float | None = None
    spp_price: float | None = None


class PromoInfo(BaseModel):
    """Active/upcoming promotion for this product."""

    promo_name: str
    promo_price: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    promo_margin_pct: float | None = None


class PriceOrderBucket(BaseModel):
    """Orders grouped by price level."""

    price: float
    spp_price: float | None = None
    orders_count: int = 0


class WeekdayOrders(BaseModel):
    """Average orders by day of week."""

    weekday: int  # 0=Mon, 6=Sun
    weekday_name: str
    avg_orders: float = 0


class FunnelDataPoint(BaseModel):
    """Daily funnel data from nm-report (views → cart → orders → buyouts)."""

    date: date
    views: int = 0
    cart: int = 0
    orders: int = 0
    buyouts: int = 0
    cancels: int = 0
    wishlist: int = 0
    orders_sum_rub: float = 0
    buyouts_sum_rub: float = 0
    cart_conversion: float | None = None
    order_conversion: float | None = None
    buyout_pct: float | None = None


class FunnelTotals(BaseModel):
    """Aggregated funnel totals for the period."""

    views: int = 0
    cart: int = 0
    orders: int = 0
    buyouts: int = 0
    cancels: int = 0
    avg_cart_conversion: float | None = None
    avg_order_conversion: float | None = None
    avg_buyout_pct: float | None = None
    orders_sum_rub: float = 0
    buyouts_sum_rub: float = 0


class ProductAnalyticsResponse(BaseModel):
    """Full product analytics response."""

    product_id: int
    nm_id: int
    title: str | None = None
    image_url: str | None = None

    # Current metrics
    margin_pct: float | None = None
    margin_rub: float | None = None
    total_stock: int = 0
    sales_velocity_7d: float = 0
    sales_velocity_14d: float = 0
    velocity_trend_pct: float | None = None
    turnover_days: float | None = None

    # Chart data
    daily_data: list[DailyDataPoint] = []
    price_history: list[PricePoint] = []
    promo_prices: list[PromoInfo] = []
    orders_by_price: list[PriceOrderBucket] = []
    orders_by_weekday: list[WeekdayOrders] = []

    # Funnel data (from nm-report)
    funnel_data: list[FunnelDataPoint] = []
    totals_funnel: FunnelTotals | None = None

    days: int = 30
