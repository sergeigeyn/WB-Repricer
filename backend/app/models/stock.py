"""Stock history model."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockHistory(Base):
    __tablename__ = "stock_history"
    __table_args__ = (
        Index("idx_stock_history_product_date", "product_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[int | None] = mapped_column()
    warehouse_name: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(default=0)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
