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
