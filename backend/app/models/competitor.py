"""Competitor tracking models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    competitor_nm_id: Mapped[int] = mapped_column(index=True)
    competitor_brand: Mapped[str | None] = mapped_column(String(255))
    competitor_title: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_dumping: Mapped[bool] = mapped_column(default=False)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"
    __table_args__ = (
        Index("idx_competitor_prices_date", "competitor_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), index=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    spp_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    stock_quantity: Mapped[int | None] = mapped_column()
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    reviews_count: Mapped[int | None] = mapped_column()
    position: Mapped[int | None] = mapped_column()
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
