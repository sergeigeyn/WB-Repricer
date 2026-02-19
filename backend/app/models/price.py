"""Price history and snapshot models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        Index("idx_price_history_product_date", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    price_before_discount: Mapped[float] = mapped_column(Numeric(12, 2))
    discount: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    price_after_discount: Mapped[float] = mapped_column(Numeric(12, 2))
    spp_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    margin_rub: Mapped[float | None] = mapped_column(Numeric(12, 2))
    margin_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    change_reason: Mapped[str | None] = mapped_column(Text)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id"))
    is_applied: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("idx_price_snapshots_product_date", "product_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    wb_price: Mapped[float] = mapped_column(Numeric(12, 2))
    wb_discount: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    spp_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    wallet_discount: Mapped[float | None] = mapped_column(Numeric(5, 2))
    final_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    source: Mapped[str] = mapped_column(String(20), default="api")
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
