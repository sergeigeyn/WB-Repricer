"""Strategy runner: dispatches strategies to handlers, logs results."""

import json as json_module
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.price import PriceHistory
from app.models.strategy import ProductStrategy, Strategy, StrategyExecution
from app.services.strategies.base import get_strategy_handler

logger = logging.getLogger(__name__)


async def run_strategy(
    strategy_id: int,
    db: AsyncSession,
    triggered_by: str = "manual",
) -> StrategyExecution:
    """Run a single strategy and log the execution."""
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise ValueError(f"Strategy {strategy_id} not found")
    if not strategy.is_active:
        raise ValueError(f"Strategy {strategy_id} is inactive")

    execution = StrategyExecution(
        strategy_id=strategy.id,
        status="running",
        triggered_by=triggered_by,
        executed_at=datetime.now(UTC),
    )
    db.add(execution)
    await db.flush()

    handler = get_strategy_handler(strategy.type)
    if not handler:
        execution.status = "failed"
        execution.details_json = json_module.dumps(
            {"error": f"No handler for type '{strategy.type}'"}
        )
        execution.completed_at = datetime.now(UTC)
        await db.flush()
        raise ValueError(f"No handler registered for strategy type '{strategy.type}'")

    ps_result = await db.execute(
        select(ProductStrategy.product_id).where(
            ProductStrategy.strategy_id == strategy.id,
            ProductStrategy.is_active == True,  # noqa: E712
        )
    )
    product_ids = [row[0] for row in ps_result.all()]

    if not product_ids:
        execution.status = "completed"
        execution.products_processed = 0
        execution.recommendations_created = 0
        execution.completed_at = datetime.now(UTC)
        execution.details_json = json_module.dumps({"message": "No products assigned"})
        await db.flush()
        return execution

    config = {}
    if strategy.config_json:
        try:
            config = json_module.loads(strategy.config_json)
        except json_module.JSONDecodeError:
            pass

    try:
        recommendations = await handler.execute(strategy, config, product_ids, db)
    except Exception as e:
        logger.error("Strategy %d execution failed: %s", strategy.id, e)
        execution.status = "failed"
        execution.errors_count = 1
        execution.details_json = json_module.dumps({"error": str(e)})
        execution.completed_at = datetime.now(UTC)
        await db.flush()
        return execution

    saved = 0
    for rec in recommendations:
        ph = PriceHistory(
            product_id=rec.product_id,
            price_before_discount=rec.current_price,
            discount=0,
            price_after_discount=rec.recommended_price,
            margin_rub=rec.new_margin_rub,
            margin_pct=rec.new_margin_pct,
            change_reason=rec.reason,
            strategy_id=strategy.id,
            is_applied=False,
        )
        db.add(ph)
        saved += 1

    execution.status = "completed"
    execution.products_processed = len(product_ids)
    execution.recommendations_created = saved
    execution.completed_at = datetime.now(UTC)

    summary = {
        "total_products": len(product_ids),
        "recommendations": saved,
        "alert_levels": {},
    }
    for rec in recommendations:
        level = rec.alert_level
        summary["alert_levels"][level] = summary["alert_levels"].get(level, 0) + 1
    execution.details_json = json_module.dumps(summary)

    await db.flush()
    logger.info(
        "Strategy %d (%s) completed: %d products, %d recommendations",
        strategy.id,
        strategy.type,
        len(product_ids),
        saved,
    )
    return execution


async def run_all_active_strategies(triggered_by: str = "schedule") -> dict:
    """Run all active strategies. Called by Celery beat."""
    results = {
        "strategies_run": 0,
        "total_recommendations": 0,
        "errors": [],
    }

    async with async_session() as db:
        strat_result = await db.execute(
            select(Strategy)
            .where(Strategy.is_active == True)  # noqa: E712
            .order_by(Strategy.priority.asc())
        )
        strategies = list(strat_result.scalars().all())

        for strategy in strategies:
            try:
                execution = await run_strategy(
                    strategy.id, db, triggered_by=triggered_by
                )
                results["strategies_run"] += 1
                results["total_recommendations"] += execution.recommendations_created
            except Exception as e:
                results["errors"].append(f"Strategy {strategy.id}: {str(e)}")

        await db.commit()

    return results
