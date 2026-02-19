"""Strategy and product-strategy link models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STRATEGY_TYPES = (
    "sales_velocity",
    "out_of_stock",
    "promotion_booster",
    "competitor_following",
    "target_margin",
    "price_range",
    "demand_reaction",
    "scheduled",
    "locomotive",
    "ab_test",
)


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(
        Enum(*STRATEGY_TYPES, name="strategy_type"),
    )
    config_json: Mapped[str | None] = mapped_column(Text)  # JSON config
    priority: Mapped[int] = mapped_column(default=5)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProductStrategy(Base):
    __tablename__ = "product_strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id"), index=True)
    params_json: Mapped[str | None] = mapped_column(Text)  # JSON per-product overrides
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
