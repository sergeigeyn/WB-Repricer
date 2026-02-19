"""Promotion models."""

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    wb_promo_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PromotionProduct(Base):
    __tablename__ = "promotion_products"
    __table_args__ = (
        Index("idx_promo_products", "promotion_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    promo_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    current_margin: Mapped[float | None] = mapped_column(Numeric(12, 2))
    promo_margin: Mapped[float | None] = mapped_column(Numeric(12, 2))
    decision: Mapped[str | None] = mapped_column(
        Enum("enter", "exit", "skip", "pending", name="promo_decision"),
        default="pending",
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
