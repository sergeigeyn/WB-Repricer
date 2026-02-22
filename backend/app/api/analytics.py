"""General analytics endpoint."""

import json as json_module
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.price import PriceSnapshot
from app.models.product import Product, WBAccount
from app.models.sales import CardAnalyticsDaily, SalesDaily
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    DailyFunnel,
    DailyTrend,
    TopProduct,
    TotalsSummary,
    WeekdayAvg,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

MSK = timezone(timedelta(hours=3))
WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


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
    spp_price = final_price * (1 - spp_pct / 100) if spp_pct else final_price
    tax_amount = spp_price * acc_tax / 100 if acc_tax else 0
    commission_amount = final_price * (commission_pct or 0) / 100
    tariff_amount = final_price * acc_tariff / 100 if acc_tariff else 0
    ad_amount = final_price * (ad_pct or 0) / 100
    total_costs = (
        cost_price + tax_amount + commission_amount + tariff_amount
        + (logistics_cost or 0) + (storage_cost or 0) + ad_amount
        + (extra_costs_total or 0)
    )
    margin_rub = round(final_price - total_costs, 2)
    margin_pct = round(margin_rub / final_price * 100, 1) if final_price > 0 else 0
    return margin_pct, margin_rub


def _period_days(period: str) -> int:
    return {"7d": 7, "14d": 14, "30d": 30, "60d": 60, "90d": 90}.get(period, 30)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    period: str = "30d",
    account_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get analytics overview: trends, funnel, top products, weekday averages."""
    if period not in ("7d", "14d", "30d", "60d", "90d"):
        period = "30d"

    days = _period_days(period)
    today = datetime.now(MSK).date()
    start_date = today - timedelta(days=days)

    # --- Load products ---
    prod_query = select(Product)
    if account_id is not None:
        prod_query = prod_query.where(Product.account_id == account_id)
    prod_result = await db.execute(prod_query)
    all_products = list(prod_result.scalars().all())
    product_map = {p.id: p for p in all_products}
    pid_set = {p.id for p in all_products}

    if not all_products:
        return AnalyticsOverviewResponse(
            totals=TotalsSummary(), period=period, account_id=account_id
        )

    # --- Latest prices ---
    snap_result = await db.execute(
        select(PriceSnapshot)
        .distinct(PriceSnapshot.product_id)
        .order_by(PriceSnapshot.product_id, PriceSnapshot.collected_at.desc())
    )
    snapshots = {s.product_id: s for s in snap_result.scalars().all()}

    # --- Account settings ---
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

    # --- Margins ---
    product_prices: dict[int, float] = {}
    product_margins: dict[int, float] = {}

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
                    extra_total = sum(
                        item.get("value", 0) for item in raw if item.get("type") == "fixed"
                    )
                except (json_module.JSONDecodeError, TypeError):
                    pass

            acc_tax, acc_tariff = acc_settings.get(p.account_id, (0.0, 0.0))
            _, m_rub = _calc_margin(
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

    # --- Daily trend (orders, revenue, profit) ---
    sales_query = (
        select(
            SalesDaily.date,
            SalesDaily.product_id,
            SalesDaily.orders_count,
            SalesDaily.returns_count,
            SalesDaily.revenue,
        )
        .where(SalesDaily.date >= start_date)
    )
    if account_id is not None:
        sales_query = sales_query.where(SalesDaily.product_id.in_(pid_set))

    sales_result = await db.execute(sales_query.order_by(SalesDaily.date))
    sales_rows = sales_result.all()

    # Aggregate by date
    date_data: dict[date, dict] = defaultdict(lambda: {"orders": 0, "revenue": 0.0, "profit": 0.0})
    product_totals: dict[int, dict] = defaultdict(lambda: {"orders": 0, "revenue": 0.0})

    for row in sales_rows:
        sd_date, pid, oc, rc, rev = row
        net = max((oc or 0) - (rc or 0), 0)
        price = product_prices.get(pid, 0)
        margin = product_margins.get(pid, 0)
        revenue = net * price if price else float(rev or 0)
        profit = net * margin

        date_data[sd_date]["orders"] += net
        date_data[sd_date]["revenue"] += revenue
        date_data[sd_date]["profit"] += profit

        product_totals[pid]["orders"] += net
        product_totals[pid]["revenue"] += revenue

    daily_trend = [
        DailyTrend(date=d, orders=v["orders"], revenue=round(v["revenue"], 2), profit=round(v["profit"], 2))
        for d, v in sorted(date_data.items())
    ]

    # --- Top products ---
    total_orders = sum(v["orders"] for v in product_totals.values())
    sorted_products = sorted(product_totals.items(), key=lambda x: x[1]["orders"], reverse=True)[:10]
    top_products = []
    for pid, vals in sorted_products:
        if vals["orders"] == 0:
            continue
        p = product_map.get(pid)
        if not p:
            continue
        top_products.append(TopProduct(
            product_id=pid,
            nm_id=p.nm_id,
            title=p.title,
            image_url=p.image_url,
            orders=vals["orders"],
            revenue=round(vals["revenue"], 2),
            share_pct=round(vals["orders"] / total_orders * 100, 1) if total_orders > 0 else 0,
        ))

    # --- Weekday averages ---
    weekday_data: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for row in sales_rows:
        sd_date, pid, oc, rc, rev = row
        net = max((oc or 0) - (rc or 0), 0)
        price = product_prices.get(pid, 0)
        revenue = net * price if price else float(rev or 0)
        wd = sd_date.weekday()
        weekday_data[wd].append((net, revenue))

    # Average per weekday (sum per day, then average across days)
    weekday_by_date: dict[int, dict[date, dict]] = defaultdict(lambda: defaultdict(lambda: {"orders": 0, "revenue": 0.0}))
    for row in sales_rows:
        sd_date, pid, oc, rc, rev = row
        net = max((oc or 0) - (rc or 0), 0)
        price = product_prices.get(pid, 0)
        revenue = net * price if price else float(rev or 0)
        wd = sd_date.weekday()
        weekday_by_date[wd][sd_date]["orders"] += net
        weekday_by_date[wd][sd_date]["revenue"] += revenue

    weekday_avg = []
    for wd in range(7):
        day_vals = weekday_by_date.get(wd, {})
        if day_vals:
            avg_o = round(sum(v["orders"] for v in day_vals.values()) / len(day_vals), 1)
            avg_r = round(sum(v["revenue"] for v in day_vals.values()) / len(day_vals), 0)
        else:
            avg_o, avg_r = 0, 0
        weekday_avg.append(WeekdayAvg(
            weekday=wd, weekday_name=WEEKDAY_NAMES[wd],
            avg_orders=avg_o, avg_revenue=avg_r,
        ))

    # --- Daily funnel (from card_analytics_daily) ---
    funnel_query = (
        select(
            CardAnalyticsDaily.date,
            func.sum(CardAnalyticsDaily.open_card_count),
            func.sum(CardAnalyticsDaily.add_to_cart_count),
            func.sum(CardAnalyticsDaily.orders_count),
            func.sum(CardAnalyticsDaily.buyouts_count),
        )
        .where(CardAnalyticsDaily.date >= start_date)
    )
    if account_id is not None:
        funnel_query = funnel_query.where(CardAnalyticsDaily.product_id.in_(pid_set))
    funnel_query = funnel_query.group_by(CardAnalyticsDaily.date).order_by(CardAnalyticsDaily.date)

    funnel_result = await db.execute(funnel_query)
    daily_funnel = []
    total_views = 0
    total_cart = 0
    total_funnel_orders = 0
    total_buyouts = 0

    for row in funnel_result.all():
        d, views, cart, orders, buyouts = row
        views = views or 0
        cart = cart or 0
        orders = orders or 0
        buyouts = buyouts or 0

        total_views += views
        total_cart += cart
        total_funnel_orders += orders
        total_buyouts += buyouts

        daily_funnel.append(DailyFunnel(
            date=d, views=views, cart=cart, orders=orders, buyouts=buyouts,
            cart_conversion=round(cart / views * 100, 2) if views > 0 else None,
            order_conversion=round(orders / cart * 100, 2) if cart > 0 else None,
            buyout_pct=round(buyouts / orders * 100, 1) if orders > 0 else None,
        ))

    # --- Totals ---
    sum_orders = sum(v["orders"] for v in date_data.values())
    sum_revenue = sum(v["revenue"] for v in date_data.values())
    sum_profit = sum(v["profit"] for v in date_data.values())
    avg_check = round(sum_revenue / sum_orders, 2) if sum_orders > 0 else 0

    totals = TotalsSummary(
        orders=sum_orders,
        revenue=round(sum_revenue, 2),
        profit=round(sum_profit, 2),
        avg_check=avg_check,
        views=total_views,
        cart=total_cart,
        avg_cart_conversion=round(total_cart / total_views * 100, 2) if total_views > 0 else None,
        avg_order_conversion=round(total_funnel_orders / total_cart * 100, 2) if total_cart > 0 else None,
        avg_buyout_pct=round(total_buyouts / total_funnel_orders * 100, 1) if total_funnel_orders > 0 else None,
    )

    return AnalyticsOverviewResponse(
        daily_trend=daily_trend,
        daily_funnel=daily_funnel,
        top_products=top_products,
        weekday_avg=weekday_avg,
        totals=totals,
        period=period,
        account_id=account_id,
    )
