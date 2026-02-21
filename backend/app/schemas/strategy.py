"""Strategy schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.strategy import STRATEGY_TYPES


# --- Config schemas per strategy type ---


class OutOfStockConfig(BaseModel):
    """Config schema for out_of_stock strategy."""

    threshold_days: int = Field(default=7, ge=1, le=90, description="Предупреждение: остаток < X дней")
    critical_days: int = Field(default=3, ge=1, le=30, description="Критично: остаток < X дней")
    price_increase_pct: float = Field(default=15, ge=1, le=100, description="% повышения при предупреждении")
    critical_increase_pct: float = Field(default=30, ge=1, le=100, description="% повышения при критичном")
    max_price_increase_pct: float = Field(default=50, ge=1, le=200, description="Макс допустимое повышение %")
    min_margin_pct: float = Field(default=5, ge=0, le=100, description="Мин маржа для рекомендации %")
    use_7d_velocity: bool = True
    exclude_zero_stock: bool = True


# Map of strategy type → config schema class
STRATEGY_CONFIG_SCHEMAS: dict[str, type[BaseModel]] = {
    "out_of_stock": OutOfStockConfig,
}


# --- CRUD schemas ---


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str
    config_json: dict | None = None
    priority: int = Field(default=5, ge=1, le=10)
    is_active: bool = True

    def validate_type(self) -> str:
        if self.type not in STRATEGY_TYPES:
            msg = f"Недопустимый тип. Допустимые: {', '.join(STRATEGY_TYPES)}"
            raise ValueError(msg)
        return self.type


class StrategyUpdate(BaseModel):
    name: str | None = None
    config_json: dict | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    is_active: bool | None = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    type: str
    config_json: dict | None = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    products_count: int = 0
    last_execution_at: datetime | None = None
    last_execution_status: str | None = None

    model_config = {"from_attributes": True}


class StrategyListResponse(BaseModel):
    items: list[StrategyResponse]
    total: int


class ProductStrategyAssign(BaseModel):
    product_ids: list[int]


class ProductStrategyRemove(BaseModel):
    product_ids: list[int]


# --- Execution & recommendation schemas ---


class StrategyRecommendation(BaseModel):
    product_id: int
    nm_id: int
    vendor_code: str | None = None
    title: str | None = None
    image_url: str | None = None
    total_stock: int = 0
    velocity_7d: float = 0
    days_remaining: float | None = None
    current_price: float | None = None
    recommended_price: float | None = None
    price_change_pct: float | None = None
    current_margin_pct: float | None = None
    new_margin_pct: float | None = None
    new_margin_rub: float | None = None
    alert_level: str | None = None
    reason: str | None = None
    is_applied: bool = False


class StrategyExecutionResponse(BaseModel):
    id: int
    strategy_id: int
    status: str
    products_processed: int
    recommendations_created: int
    errors_count: int
    executed_at: datetime
    completed_at: datetime | None = None
    triggered_by: str

    model_config = {"from_attributes": True}


class StrategyDetailResponse(BaseModel):
    strategy: StrategyResponse
    assigned_products: list[dict]
    last_execution: StrategyExecutionResponse | None = None
    recommendations: list[StrategyRecommendation] = []
