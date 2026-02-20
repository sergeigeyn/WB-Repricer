"""Promotion models."""

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("wb_accounts.id"), index=True)
    wb_promo_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    discount_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    promo_type: Mapped[str | None] = mapped_column(String(50))  # "regular" / "auto"
    status: Mapped[str | None] = mapped_column(String(20))  # "active" / "upcoming" / "ended"
    description: Mapped[str | None] = mapped_column(Text)
    in_action_count: Mapped[int] = mapped_column(Integer, default=0)
    total_available: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PromotionProduct(Base):
    __tablename__ = "promotion_products"
    __table_args__ = (
        Index("idx_promo_products", "promotion_id", "nm_id"),
        Index("idx_promo_products_nm", "nm_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id"), index=True)
    account_id: Mapped[int] = mapped_column(Integer, index=True)
    nm_id: Mapped[int] = mapped_column(Integer, index=True)
    plan_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    plan_discount: Mapped[float | None] = mapped_column(Numeric(5, 2))
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    in_action: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    current_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    current_margin_rub: Mapped[float | None] = mapped_column(Numeric(12, 2))
    promo_margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    promo_margin_rub: Mapped[float | None] = mapped_column(Numeric(12, 2))
    decision: Mapped[str | None] = mapped_column(String(10), default="pending")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
