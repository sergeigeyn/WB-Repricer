"""Base strategy handler and registry."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import Strategy

logger = logging.getLogger(__name__)


@dataclass
class PriceRecommendation:
    """Result from strategy calculation for a single product."""

    product_id: int
    current_price: float
    recommended_price: float
    price_change_pct: float
    current_margin_pct: float | None
    new_margin_pct: float | None
    new_margin_rub: float | None
    alert_level: str  # "safe", "warning", "critical"
    reason: str
    extra_data: dict | None = field(default=None)


class BaseStrategyHandler(ABC):
    """Abstract base class for all strategy handlers."""

    strategy_type: str

    @abstractmethod
    async def execute(
        self,
        strategy: Strategy,
        config: dict,
        product_ids: list[int],
        db: AsyncSession,
    ) -> list[PriceRecommendation]:
        """Run the strategy for given products.

        Returns: List of price recommendations.
        """
        ...


# Strategy registry
_registry: dict[str, type[BaseStrategyHandler]] = {}


def register_strategy(handler_class: type[BaseStrategyHandler]):
    """Register a strategy handler class."""
    _registry[handler_class.strategy_type] = handler_class
    return handler_class


def get_strategy_handler(strategy_type: str) -> BaseStrategyHandler | None:
    """Get handler instance for strategy type."""
    handler_class = _registry.get(strategy_type)
    if handler_class:
        return handler_class()
    return None
