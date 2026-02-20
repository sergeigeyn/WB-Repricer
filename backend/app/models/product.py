"""WB account and product models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WBAccount(Base):
    __tablename__ = "wb_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    permissions_json: Mapped[str | None] = mapped_column(Text)  # JSON list of permissions
    tax_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))  # Tax % (УСН/ОСН)
    tariff_rate: Mapped[float | None] = mapped_column(Numeric(5, 2))  # Конструктор тарифов %
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("wb_accounts.id"), index=True)
    nm_id: Mapped[int] = mapped_column(unique=True, index=True)  # WB article number
    vendor_code: Mapped[str | None] = mapped_column(String(100))
    brand: Mapped[str | None] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(255), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    barcode: Mapped[str | None] = mapped_column(String(50), index=True)
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    commission_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))  # WB commission %
    logistics_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))  # Logistics ₽ per delivery (auto from WB)
    storage_cost: Mapped[float | None] = mapped_column(Numeric(12, 2))  # Storage ₽ per sale (auto from WB)
    storage_daily: Mapped[float | None] = mapped_column(Numeric(12, 2))  # Storage ₽ total per day (auto from WB)
    ad_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))  # Advertising % of revenue
    spp_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))  # Average SPP % (auto from WB)
    extra_costs_json: Mapped[str | None] = mapped_column(Text)  # JSON list of {name, value, type}
    tag: Mapped[str | None] = mapped_column(String(100))  # User-defined tag for grouping
    total_stock: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_locomotive: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
