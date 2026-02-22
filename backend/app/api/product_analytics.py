"""Product analytics endpoint."""

import json as json_module
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.price import PriceSnapshot
from app.models.product import Product, WBAccount
from app.models.promotion import Promotion, PromotionProduct
from app.models.sales import SalesDaily
from app.models.user import User
from app.schemas.product_analytics import (
    DailyDataPoint,
    PriceOrderBucket,
    PricePoint,
    PromoInfo,
    ProductAnalyticsResponse,
    WeekdayOrders,
)

router = APIRouter(prefix="/products", tags=["product-analytics"])

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
    """Calculate (margin_pct, margin_rub). Same formula as dashboard.py."""
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


@router.get("/{product_id}/analytics", response_model=ProductAnalyticsResponse)
async def get_product_analytics(
    product_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Get analytics data for a specific product."""
    if days not in (7, 14, 30, 60, 90):
        days = 30

    # --- Load product ---
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    today = datetime.now(MSK).date()
    start_date = today - timedelta(days=days)

    # --- Account settings ---
    acc_result = await db.execute(
        select(WBAccount.tax_rate, WBAccount.tariff_rate)
        .where(WBAccount.id == product.account_id)
    )
    acc_row = acc_result.one_or_none()
    acc_tax = float(acc_row[0]) if acc_row and acc_row[0] else 0.0
    acc_tariff = float(acc_row[1]) if acc_row and acc_row[1] else 0.0

    # --- Current margin ---
    snap_result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .order_by(PriceSnapshot.collected_at.desc())
        .limit(1)
    )
    latest_snap = snap_result.scalars().first()
    fp = float(latest_snap.final_price) if latest_snap and latest_snap.final_price else None
    cp = float(product.cost_price) if product.cost_price is not None else None

    margin_pct = None
    margin_rub = None
    if fp and cp and fp > 0:
        extra_total = 0.0
        if product.extra_costs_json:
            try:
                raw = json_module.loads(product.extra_costs_json)
                extra_total = sum(
                    item.get("value", 0) for item in raw if item.get("type") == "fixed"
                )
            except (json_module.JSONDecodeError, TypeError):
                pass

        margin_pct, margin_rub = _calc_margin(
            fp, cp,
            float(product.commission_pct) if product.commission_pct is not None else None,
            float(product.logistics_cost) if product.logistics_cost is not None else None,
            float(product.storage_cost) if product.storage_cost is not None else None,
            float(product.ad_pct) if product.ad_pct is not None else None,
            float(product.spp_pct) if product.spp_pct is not None else None,
            extra_total or None,
            acc_tax, acc_tariff,
        )

    # --- Sales daily data ---
    sales_result = await db.execute(
        select(SalesDaily)
        .where(SalesDaily.product_id == product_id, SalesDaily.date >= start_date)
        .order_by(SalesDaily.date)
    )
    sales_rows = list(sales_result.scalars().all())

    # --- Price snapshots per day (DISTINCT ON date) ---
    price_result = await db.execute(
        select(
            cast(PriceSnapshot.collected_at, Date).label("snap_date"),
            PriceSnapshot.final_price,
            PriceSnapshot.spp_percent,
        )
        .where(
            PriceSnapshot.product_id == product_id,
            PriceSnapshot.collected_at >= datetime(
                start_date.year, start_date.month, start_date.day, tzinfo=MSK
            ),
        )
        .distinct(cast(PriceSnapshot.collected_at, Date))
        .order_by(cast(PriceSnapshot.collected_at, Date), PriceSnapshot.collected_at.desc())
    )
    price_by_date: dict[date, tuple[float, float | None]] = {}
    for row in price_result.all():
        snap_date = row[0]
        pfp = float(row[1]) if row[1] else None
        spp = float(row[2]) if row[2] else None
        if pfp:
            price_by_date[snap_date] = (pfp, spp)

    # --- Build daily_data ---
    spp_pct_val = float(product.spp_pct) if product.spp_pct is not None else None
    daily_data: list[DailyDataPoint] = []
    for sd in sales_rows:
        price_info = price_by_date.get(sd.date)
        price_val = price_info[0] if price_info else None
        spp_price_val = None
        if price_val and spp_pct_val:
            spp_price_val = round(price_val * (1 - spp_pct_val / 100), 2)

        daily_data.append(DailyDataPoint(
            date=sd.date,
            orders=sd.orders_count or 0,
            returns=sd.returns_count or 0,
            net_orders=max((sd.orders_count or 0) - (sd.returns_count or 0), 0),
            price=price_val,
            spp_price=spp_price_val,
        ))

    # --- Price history ---
    price_history: list[PricePoint] = []
    for snap_date, (pfp, spp) in sorted(price_by_date.items()):
        spp_price_val = None
        if pfp and spp_pct_val:
            spp_price_val = round(pfp * (1 - spp_pct_val / 100), 2)
        price_history.append(PricePoint(
            date=snap_date,
            final_price=pfp,
            spp_pct=spp_pct_val,
            spp_price=spp_price_val,
        ))

    # --- Promotions ---
    promo_result = await db.execute(
        select(Promotion.name, PromotionProduct.promo_price,
               Promotion.start_date, Promotion.end_date,
               PromotionProduct.promo_margin_pct)
        .join(Promotion, PromotionProduct.promotion_id == Promotion.id)
        .where(
            PromotionProduct.nm_id == product.nm_id,
            Promotion.status.in_(["active", "upcoming"]),
        )
    )
    promo_prices = [
        PromoInfo(
            promo_name=row[0],
            promo_price=float(row[1]) if row[1] else None,
            start_date=row[2],
            end_date=row[3],
            promo_margin_pct=float(row[4]) if row[4] else None,
        )
        for row in promo_result.all()
    ]

    # --- Orders by price bucket ---
    price_orders: dict[float, int] = defaultdict(int)
    for dp in daily_data:
        if dp.price and dp.net_orders > 0:
            rounded = round(dp.price)
            price_orders[rounded] += dp.net_orders

    orders_by_price = [
        PriceOrderBucket(
            price=p,
            spp_price=round(p * (1 - spp_pct_val / 100), 2) if spp_pct_val else None,
            orders_count=cnt,
        )
        for p, cnt in sorted(price_orders.items())
    ]

    # --- Orders by weekday ---
    weekday_orders: dict[int, list[int]] = defaultdict(list)
    for sd in sales_rows:
        # Python: Monday=0, Sunday=6
        wd = sd.date.weekday()
        net = max((sd.orders_count or 0) - (sd.returns_count or 0), 0)
        weekday_orders[wd].append(net)

    orders_by_weekday = []
    for wd in range(7):
        vals = weekday_orders.get(wd, [])
        avg = round(sum(vals) / len(vals), 1) if vals else 0
        orders_by_weekday.append(WeekdayOrders(
            weekday=wd,
            weekday_name=WEEKDAY_NAMES[wd],
            avg_orders=avg,
        ))

    # --- Sales velocity ---
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)

    orders_7d = sum(
        max((sd.orders_count or 0) - (sd.returns_count or 0), 0)
        for sd in sales_rows if sd.date >= seven_days_ago
    )
    orders_14d = sum(
        max((sd.orders_count or 0) - (sd.returns_count or 0), 0)
        for sd in sales_rows if sd.date >= fourteen_days_ago
    )

    velocity_7d = round(orders_7d / 7, 2)
    velocity_14d = round(orders_14d / 14, 2)

    velocity_trend = None
    if velocity_14d > 0:
        velocity_trend = round((velocity_7d - velocity_14d) / velocity_14d * 100, 1)

    turnover = None
    if velocity_7d > 0 and (product.total_stock or 0) > 0:
        turnover = round((product.total_stock or 0) / velocity_7d, 1)

    return ProductAnalyticsResponse(
        product_id=product.id,
        nm_id=product.nm_id,
        title=product.title,
        image_url=product.image_url,
        margin_pct=margin_pct,
        margin_rub=margin_rub,
        total_stock=product.total_stock or 0,
        sales_velocity_7d=velocity_7d,
        sales_velocity_14d=velocity_14d,
        velocity_trend_pct=velocity_trend,
        turnover_days=turnover,
        daily_data=daily_data,
        price_history=price_history,
        promo_prices=promo_prices,
        orders_by_price=orders_by_price,
        orders_by_weekday=orders_by_weekday,
        days=days,
    )
