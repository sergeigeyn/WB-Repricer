"""Strategy framework: base class, registry, and handlers."""

# Import handlers to trigger @register_strategy decorators
from app.services.strategies.out_of_stock import OutOfStockHandler  # noqa: F401
