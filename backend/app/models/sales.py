"""Sales daily and hourly models."""

from datetime import date, datetime, UTC

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SalesDaily(Base):
    __tablename__ = "sales_daily"
    __table_args__ = (
        Index("idx_sales_daily_product_date", "product_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    orders_count: Mapped[int] = mapped_column(default=0)
    sales_count: Mapped[int] = mapped_column(default=0)
    returns_count: Mapped[int] = mapped_column(default=0)
    cancel_count: Mapped[int] = mapped_column(default=0)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    cart_adds: Mapped[int] = mapped_column(default=0)
    avg_price_spp: Mapped[float | None] = mapped_column(Numeric(12, 2))


class CardAnalyticsDaily(Base):
    """Daily card analytics from WB nm-report API (views, cart, conversions)."""

    __tablename__ = "card_analytics_daily"
    __table_args__ = (
        Index("idx_card_analytics_product_date", "product_id", "date", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open_card_count: Mapped[int] = mapped_column(default=0)
    add_to_cart_count: Mapped[int] = mapped_column(default=0)
    orders_count: Mapped[int] = mapped_column(default=0)
    orders_sum_rub: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    buyouts_count: Mapped[int] = mapped_column(default=0)
    buyouts_sum_rub: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    cancel_count: Mapped[int] = mapped_column(default=0)
    cancel_sum_rub: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    add_to_cart_conversion: Mapped[float | None] = mapped_column(Numeric(6, 2))
    cart_to_order_conversion: Mapped[float | None] = mapped_column(Numeric(6, 2))
    buyout_percent: Mapped[float | None] = mapped_column(Numeric(6, 2))
    add_to_wishlist: Mapped[int] = mapped_column(default=0)


class SalesHourly(Base):
    __tablename__ = "sales_hourly"
    __table_args__ = (
        Index("idx_sales_hourly_product_date", "product_id", "date", "hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    hour: Mapped[int] = mapped_column()  # 0-23
    orders_count: Mapped[int] = mapped_column(default=0)
    cart_adds: Mapped[int] = mapped_column(default=0)
