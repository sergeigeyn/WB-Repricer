"""Dashboard endpoint."""

import json as json_module
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.price import PriceHistory, PriceSnapshot
from app.models.product import Product, WBAccount
from app.models.promotion import Promotion, PromotionProduct
from app.models.sales import SalesDaily
from app.models.strategy import ProductStrategy
from app.models.user import User
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardKPI,
    DashboardPromotion,
    DashboardResponse,
    DashboardTopProduct,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MSK = timezone(timedelta(hours=3))


def _period_range(period: str) -> tuple[date, date, date, date]:
    """Return (start, end, prev_start, prev_end) for given period string."""
    today = datetime.now(MSK).date()
    if period == "today":
        start = today
        end = today + timedelta(days=1)
        prev_start = today - timedelta(days=1)
        prev_end = today
    elif period == "30d":
        start = today - timedelta(days=30)
        end = today
        prev_start = today - timedelta(days=60)
        prev_end = start
    else:  # 7d default
        start = today - timedelta(days=7)
        end = today
        prev_start = today - timedelta(days=14)
        prev_end = start
    return start, end, prev_start, prev_end


def _calc_margin(
    final_price: float,
    cost_price: float,
    commission_pct: float | None,
    logistics_cost: float | None,
    storage_cost: float | None,
    ad_pct: float | None,
    spp_pct: float | None,
    extra_costs_total: float | None,
    acc_tax: float,
    acc_tariff: float,
) -> tuple[float, float]:
    """Calculate (margin_pct, margin_rub). Same formula as products.py:115-132."""
    spp_price = final_price * (1 - spp_pct / 100) if spp_pct else final_price
    tax_amount = spp_price * acc_tax / 100 if acc_tax else 0
    commission_amount = final_price * (commission_pct or 0) / 100
    tariff_amount = final_price * acc_tariff / 100 if acc_tariff else 0
    ad_amount = final_price * (ad_pct or 0) / 100
    total_costs = (
        cost_price
        + tax_amount
        + commission_amount
        + tariff_amount
        + (logistics_cost or 0)
        + (storage_cost or 0)
        + ad_amount
        + (extra_costs_total or 0)
    )
    margin_rub = round(final_price - total_costs, 2)
    margin_pct = round(margin_rub / final_price * 100, 1) if final_price > 0 else 0
    return margin_pct, margin_rub


async def _calc_period_totals(
    db: AsyncSession,
    start: date,
    end: date,
    product_prices: dict[int, float],
    product_margins: dict[int, float],
) -> tuple[int, float, float]:
    """Calculate total orders, revenue, profit for a period."""
    result = await db.execute(
        select(
            SalesDaily.product_id,
            func.sum(SalesDaily.orders_count),
            func.sum(SalesDaily.returns_count),
        )
        .where(SalesDaily.date >= start, SalesDaily.date < end)
        .group_by(SalesDaily.product_id)
    )
    total_orders = 0
    total_revenue = 0.0
    total_profit = 0.0
    for row in result.all():
        pid = row[0]
        net = max((row[1] or 0) - (row[2] or 0), 0)
        total_orders += net
        price = product_prices.get(pid, 0)
        margin = product_margins.get(pid, 0)
        total_revenue += net * price
        total_profit += net * margin
    return total_orders, round(total_revenue, 2), round(total_profit, 2)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    period: str = "7d",
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get dashboard KPIs, alerts, promotions, and top products."""
    if period not in ("today", "7d", "30d"):
        period = "7d"

    start, end, prev_start, prev_end = _period_range(period)
    today = datetime.now(MSK).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=MSK)

    # --- Load all active products ---
    prod_result = await db.execute(select(Product))
    all_products = list(prod_result.scalars().all())
    product_map = {p.id: p for p in all_products}

    # --- Latest price snapshots ---
    snap_result = await db.execute(
        select(PriceSnapshot)
        .distinct(PriceSnapshot.product_id)
        .order_by(PriceSnapshot.product_id, PriceSnapshot.collected_at.desc())
    )
    snapshots = {s.product_id: s for s in snap_result.scalars().all()}

    # --- Account settings (tax, tariff) ---
    account_ids = {p.account_id for p in all_products}
    acc_settings: dict[int, tuple[float, float]] = {}
    if account_ids:
        acc_result = await db.execute(
            select(WBAccount.id, WBAccount.tax_rate, WBAccount.tariff_rate)
            .where(WBAccount.id.in_(account_ids))
        )
        for row in acc_result.all():
            acc_settings[row[0]] = (
                float(row[1]) if row[1] else 0.0,
                float(row[2]) if row[2] else 0.0,
            )

    # --- Calculate margin per product ---
    product_prices: dict[int, float] = {}
    product_margins: dict[int, float] = {}
    product_margin_pcts: dict[int, float] = {}

    for p in all_products:
        snap = snapshots.get(p.id)
        fp = float(snap.final_price) if snap and snap.final_price else None
        cp = float(p.cost_price) if p.cost_price is not None else None

        if fp and fp > 0:
            product_prices[p.id] = fp

        if fp and cp and fp > 0:
            extra_total = 0.0
            if p.extra_costs_json:
                try:
                    raw = json_module.loads(p.extra_costs_json)
                    extra_total = sum(item.get("value", 0) for item in raw if item.get("type") == "fixed")
                except (json_module.JSONDecodeError, TypeError):
                    pass

            acc_tax, acc_tariff = acc_settings.get(p.account_id, (0.0, 0.0))
            m_pct, m_rub = _calc_margin(
                fp, cp,
                float(p.commission_pct) if p.commission_pct is not None else None,
                float(p.logistics_cost) if p.logistics_cost is not None else None,
                float(p.storage_cost) if p.storage_cost is not None else None,
                float(p.ad_pct) if p.ad_pct is not None else None,
                float(p.spp_pct) if p.spp_pct is not None else None,
                extra_total or None,
                acc_tax, acc_tariff,
            )
            product_margins[p.id] = m_rub
            product_margin_pcts[p.id] = m_pct

    # --- KPI: Orders, Revenue, Profit ---
    cur_orders, cur_revenue, cur_profit = await _calc_period_totals(
        db, start, end, product_prices, product_margins
    )
    prev_orders, prev_revenue, prev_profit = await _calc_period_totals(
        db, prev_start, prev_end, product_prices, product_margins
    )

    def _pct_change(cur: float, prev: float) -> float | None:
        if prev and prev > 0:
            return round((cur - prev) / prev * 100, 1)
        return None

    # Weighted average margin
    avg_margin = None
    if cur_revenue > 0:
        avg_margin = round(cur_profit / cur_revenue * 100, 1)

    # --- Operational KPI ---
    active_products = sum(1 for p in all_products if (p.total_stock or 0) > 0)
    total_stock = sum(p.total_stock or 0 for p in all_products)

    # Price changes today
    pc_result = await db.execute(
        select(func.count(PriceHistory.id)).where(PriceHistory.created_at >= today_start)
    )
    price_changes_today = pc_result.scalar() or 0

    kpi = DashboardKPI(
        total_orders=cur_orders,
        total_revenue=cur_revenue,
        total_profit=cur_profit,
        avg_margin_pct=avg_margin,
        orders_change_pct=_pct_change(cur_orders, prev_orders),
        revenue_change_pct=_pct_change(cur_revenue, prev_revenue),
        profit_change_pct=_pct_change(cur_profit, prev_profit),
        active_products=active_products,
        total_products=len(all_products),
        total_stock=total_stock,
        price_changes_today=price_changes_today,
    )

    # --- Alerts: products with margin issues ---
    alerts: list[DashboardAlert] = []
    for p in all_products:
        if (p.total_stock or 0) <= 0:
            continue
        m_pct = product_margin_pcts.get(p.id)
        if m_pct is None:
            continue
        if m_pct < 0:
            alerts.append(DashboardAlert(
                type="negative_margin",
                severity="critical",
                product_id=p.id,
                nm_id=p.nm_id,
                title=p.title,
                image_url=p.image_url,
                value=m_pct,
                detail=f"Маржа {m_pct}%",
            ))
        elif m_pct < 10:
            alerts.append(DashboardAlert(
                type="low_margin",
                severity="warning",
                product_id=p.id,
                nm_id=p.nm_id,
                title=p.title,
                image_url=p.image_url,
                value=m_pct,
                detail=f"Маржа {m_pct}%",
            ))

    # Sort alerts: critical first, then by margin ascending
    alerts.sort(key=lambda a: (0 if a.severity == "critical" else 1, a.value or 0))
    alerts = alerts[:20]

    # --- Products without strategy ---
    ps_result = await db.execute(
        select(ProductStrategy.product_id).where(ProductStrategy.is_active == True)  # noqa: E712
    )
    assigned_ids = {row[0] for row in ps_result.all()}
    without_strategy = sum(
        1 for p in all_products if (p.total_stock or 0) > 0 and p.id not in assigned_ids
    )

    # --- Products without cost price ---
    without_cost = sum(
        1 for p in all_products if (p.total_stock or 0) > 0 and p.cost_price is None
    )

    # --- Active promotions ---
    promo_result = await db.execute(
        select(Promotion)
        .where(Promotion.status.in_(["active", "upcoming"]), Promotion.is_active == True)  # noqa: E712
        .order_by(Promotion.start_date.asc())
        .limit(5)
    )
    promos = list(promo_result.scalars().all())

    active_promotions: list[DashboardPromotion] = []
    for promo in promos:
        agg = await db.execute(
            select(
                func.avg(PromotionProduct.promo_margin_pct),
                func.count().filter(PromotionProduct.promo_margin_pct > 0),
            ).where(PromotionProduct.promotion_id == promo.id)
        )
        row = agg.one()
        avg_pm = round(float(row[0]), 1) if row[0] is not None else None
        profitable = row[1] or 0

        active_promotions.append(DashboardPromotion(
            id=promo.id,
            name=promo.name,
            status=promo.status or "active",
            start_date=promo.start_date,
            end_date=promo.end_date,
            in_action_count=promo.in_action_count or 0,
            total_available=promo.total_available or 0,
            avg_promo_margin=avg_pm,
            profitable_count=profitable,
        ))

    # --- Top products by orders ---
    top_q = await db.execute(
        select(
            SalesDaily.product_id,
            func.sum(SalesDaily.orders_count).label("total_orders"),
            func.sum(SalesDaily.returns_count).label("total_returns"),
        )
        .where(SalesDaily.date >= start, SalesDaily.date < end)
        .group_by(SalesDaily.product_id)
        .order_by(func.sum(SalesDaily.orders_count).desc())
        .limit(10)
    )

    top_products: list[DashboardTopProduct] = []
    for row in top_q.all():
        pid = row[0]
        net = max((row[1] or 0) - (row[2] or 0), 0)
        p = product_map.get(pid)
        if not p or net == 0:
            continue
        price = product_prices.get(pid, 0)
        top_products.append(DashboardTopProduct(
            product_id=pid,
            nm_id=p.nm_id,
            title=p.title,
            image_url=p.image_url,
            orders=net,
            revenue=round(net * price, 2),
            margin_pct=product_margin_pcts.get(pid),
            margin_rub=product_margins.get(pid),
        ))

    return DashboardResponse(
        kpi=kpi,
        alerts=alerts,
        active_promotions=active_promotions,
        top_products=top_products,
        products_without_strategy=without_strategy,
        products_without_cost=without_cost,
        period=period,
    )
