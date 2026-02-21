"""Strategy endpoints."""

import json as json_module
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.price import PriceHistory, PriceSnapshot
from app.models.product import Product
from app.models.strategy import STRATEGY_TYPES, ProductStrategy, Strategy, StrategyExecution
from app.models.user import User
from app.schemas.strategy import (
    STRATEGY_CONFIG_SCHEMAS,
    ProductStrategyAssign,
    ProductStrategyRemove,
    StrategyCreate,
    StrategyDetailResponse,
    StrategyExecutionResponse,
    StrategyListResponse,
    StrategyRecommendation,
    StrategyResponse,
    StrategyUpdate,
)
from app.services.strategies.runner import run_strategy

# Ensure handlers are registered
import app.services.strategies  # noqa: F401

router = APIRouter(prefix="/strategies", tags=["strategies"])


# --- Helpers ---


async def _build_strategy_response(
    db: AsyncSession, strategy: Strategy
) -> StrategyResponse:
    """Build StrategyResponse with aggregated data."""
    # Products count
    cnt_result = await db.execute(
        select(func.count(ProductStrategy.id)).where(
            ProductStrategy.strategy_id == strategy.id,
            ProductStrategy.is_active == True,  # noqa: E712
        )
    )
    products_count = cnt_result.scalar() or 0

    # Last execution
    exec_result = await db.execute(
        select(StrategyExecution)
        .where(StrategyExecution.strategy_id == strategy.id)
        .order_by(StrategyExecution.executed_at.desc())
        .limit(1)
    )
    last_exec = exec_result.scalar_one_or_none()

    config = None
    if strategy.config_json:
        try:
            config = json_module.loads(strategy.config_json)
        except json_module.JSONDecodeError:
            config = None

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        type=strategy.type,
        config_json=config,
        priority=strategy.priority,
        is_active=strategy.is_active,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
        products_count=products_count,
        last_execution_at=last_exec.executed_at if last_exec else None,
        last_execution_status=last_exec.status if last_exec else None,
    )


# --- Endpoints ---


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    type: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List strategies with product count and last execution info."""
    query = select(Strategy).order_by(Strategy.priority.asc(), Strategy.created_at.desc())
    if type:
        query = query.where(Strategy.type == type)
    if is_active is not None:
        query = query.where(Strategy.is_active == is_active)

    result = await db.execute(query)
    strategies = list(result.scalars().all())

    items = []
    for s in strategies:
        items.append(await _build_strategy_response(db, s))

    return StrategyListResponse(items=items, total=len(items))


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    data: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new strategy."""
    if data.type not in STRATEGY_TYPES:
        raise HTTPException(400, f"Недопустимый тип. Допустимые: {', '.join(STRATEGY_TYPES)}")

    strategy = Strategy(
        name=data.name,
        type=data.type,
        config_json=json_module.dumps(data.config_json) if data.config_json else None,
        priority=data.priority,
        is_active=data.is_active,
        created_by=current_user.id,
    )
    db.add(strategy)
    await db.flush()
    await db.commit()
    await db.refresh(strategy)

    return await _build_strategy_response(db, strategy)


@router.get("/config-schema/{strategy_type}")
async def get_config_schema(strategy_type: str):
    """Return JSON Schema for strategy config by type."""
    schema_cls = STRATEGY_CONFIG_SCHEMAS.get(strategy_type)
    if not schema_cls:
        raise HTTPException(404, f"Схема не найдена для типа '{strategy_type}'")
    return schema_cls.model_json_schema()


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy_detail(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get strategy details with assigned products and latest recommendations."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Стратегия не найдена")

    strategy_resp = await _build_strategy_response(db, strategy)

    # Assigned products with basic info
    ps_result = await db.execute(
        select(ProductStrategy.product_id).where(
            ProductStrategy.strategy_id == strategy.id,
            ProductStrategy.is_active == True,  # noqa: E712
        )
    )
    product_ids = [row[0] for row in ps_result.all()]

    assigned_products = []
    if product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        # Get latest prices for these products
        snap_result = await db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id.in_(product_ids))
            .distinct(PriceSnapshot.product_id)
            .order_by(PriceSnapshot.product_id, PriceSnapshot.collected_at.desc())
        )
        snapshots = {s.product_id: s for s in snap_result.scalars().all()}

        for p in prod_result.scalars().all():
            snap = snapshots.get(p.id)
            assigned_products.append({
                "id": p.id,
                "nm_id": p.nm_id,
                "vendor_code": p.vendor_code,
                "title": p.title,
                "image_url": p.image_url,
                "total_stock": p.total_stock or 0,
                "current_price": float(snap.final_price) if snap and snap.final_price else None,
            })

    # Last execution
    exec_result = await db.execute(
        select(StrategyExecution)
        .where(StrategyExecution.strategy_id == strategy.id)
        .order_by(StrategyExecution.executed_at.desc())
        .limit(1)
    )
    last_exec = exec_result.scalar_one_or_none()
    last_exec_resp = None
    if last_exec:
        last_exec_resp = StrategyExecutionResponse(
            id=last_exec.id,
            strategy_id=last_exec.strategy_id,
            status=last_exec.status,
            products_processed=last_exec.products_processed,
            recommendations_created=last_exec.recommendations_created,
            errors_count=last_exec.errors_count,
            executed_at=last_exec.executed_at,
            completed_at=last_exec.completed_at,
            triggered_by=last_exec.triggered_by,
        )

    # Recommendations from latest execution (from price_history)
    recommendations = []
    if last_exec and last_exec.status == "completed" and last_exec.recommendations_created > 0:
        ph_result = await db.execute(
            select(PriceHistory)
            .where(
                PriceHistory.strategy_id == strategy.id,
                PriceHistory.created_at >= last_exec.executed_at,
            )
            .order_by(PriceHistory.created_at.desc())
        )
        price_histories = list(ph_result.scalars().all())

        # Get product info for recommendations
        ph_product_ids = [ph.product_id for ph in price_histories]
        if ph_product_ids:
            prod_result2 = await db.execute(
                select(Product).where(Product.id.in_(ph_product_ids))
            )
            products_map = {p.id: p for p in prod_result2.scalars().all()}

            for ph in price_histories:
                prod = products_map.get(ph.product_id)
                if not prod:
                    continue
                # Infer alert_level from change_reason
                alert_level = None
                reason = ph.change_reason or ""
                if "КРИТИЧНО" in reason:
                    alert_level = "critical"
                elif "Предупреждение" in reason:
                    alert_level = "warning"

                recommendations.append(
                    StrategyRecommendation(
                        product_id=ph.product_id,
                        nm_id=prod.nm_id,
                        vendor_code=prod.vendor_code,
                        title=prod.title,
                        image_url=prod.image_url,
                        total_stock=prod.total_stock or 0,
                        current_price=float(ph.price_before_discount) if ph.price_before_discount else None,
                        recommended_price=float(ph.price_after_discount) if ph.price_after_discount else None,
                        price_change_pct=(
                            round(
                                (float(ph.price_after_discount) - float(ph.price_before_discount))
                                / float(ph.price_before_discount)
                                * 100,
                                1,
                            )
                            if ph.price_before_discount and ph.price_after_discount
                            else None
                        ),
                        new_margin_pct=float(ph.margin_pct) if ph.margin_pct else None,
                        new_margin_rub=float(ph.margin_rub) if ph.margin_rub else None,
                        alert_level=alert_level,
                        reason=ph.change_reason,
                        is_applied=ph.is_applied,
                    )
                )

    return StrategyDetailResponse(
        strategy=strategy_resp,
        assigned_products=assigned_products,
        last_execution=last_exec_resp,
        recommendations=recommendations,
    )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Update strategy config, name, priority, or active status."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Стратегия не найдена")

    if data.name is not None:
        strategy.name = data.name
    if data.config_json is not None:
        strategy.config_json = json_module.dumps(data.config_json)
    if data.priority is not None:
        strategy.priority = data.priority
    if data.is_active is not None:
        strategy.is_active = data.is_active

    await db.flush()
    await db.commit()
    await db.refresh(strategy)

    return await _build_strategy_response(db, strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Deactivate strategy (soft delete)."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "Стратегия не найдена")

    strategy.is_active = False
    await db.flush()
    await db.commit()
    return {"message": "Стратегия деактивирована"}


@router.post("/{strategy_id}/products")
async def assign_products(
    strategy_id: int,
    data: ProductStrategyAssign,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Assign products to strategy."""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Стратегия не найдена")

    # Get existing assignments
    existing_result = await db.execute(
        select(ProductStrategy.product_id).where(
            ProductStrategy.strategy_id == strategy_id,
            ProductStrategy.is_active == True,  # noqa: E712
        )
    )
    existing_ids = {row[0] for row in existing_result.all()}

    added = 0
    for pid in data.product_ids:
        if pid not in existing_ids:
            db.add(ProductStrategy(
                product_id=pid,
                strategy_id=strategy_id,
                is_active=True,
            ))
            added += 1

    await db.flush()
    await db.commit()
    return {"message": f"Добавлено {added} товаров", "added": added}


@router.delete("/{strategy_id}/products")
async def remove_products(
    strategy_id: int,
    data: ProductStrategyRemove,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Remove products from strategy."""
    result = await db.execute(
        select(ProductStrategy).where(
            ProductStrategy.strategy_id == strategy_id,
            ProductStrategy.product_id.in_(data.product_ids),
            ProductStrategy.is_active == True,  # noqa: E712
        )
    )
    links = list(result.scalars().all())
    removed = 0
    for link in links:
        link.is_active = False
        removed += 1

    await db.flush()
    await db.commit()
    return {"message": f"Отвязано {removed} товаров", "removed": removed}


@router.post("/{strategy_id}/run")
async def run_strategy_endpoint(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Run strategy manually (dry run — recommendations only)."""
    try:
        execution = await run_strategy(strategy_id, db, triggered_by="manual")
    except ValueError as e:
        raise HTTPException(400, str(e))

    await db.commit()

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "products_processed": execution.products_processed,
        "recommendations_created": execution.recommendations_created,
        "errors_count": execution.errors_count,
    }


@router.get("/{strategy_id}/executions", response_model=list[StrategyExecutionResponse])
async def list_executions(
    strategy_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List strategy execution history."""
    result = await db.execute(
        select(StrategyExecution)
        .where(StrategyExecution.strategy_id == strategy_id)
        .order_by(StrategyExecution.executed_at.desc())
        .limit(limit)
    )
    executions = list(result.scalars().all())
    return [
        StrategyExecutionResponse(
            id=e.id,
            strategy_id=e.strategy_id,
            status=e.status,
            products_processed=e.products_processed,
            recommendations_created=e.recommendations_created,
            errors_count=e.errors_count,
            executed_at=e.executed_at,
            completed_at=e.completed_at,
            triggered_by=e.triggered_by,
        )
        for e in executions
    ]
