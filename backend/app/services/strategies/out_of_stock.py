"""Out-of-stock protection strategy handler."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import PriceSnapshot
from app.models.product import Product, WBAccount
from app.models.sales import SalesDaily
from app.models.strategy import Strategy
from app.services.promotion_collector import calculate_promo_margin
from app.services.strategies.base import (
    BaseStrategyHandler,
    PriceRecommendation,
    register_strategy,
)

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))

DEFAULT_CONFIG = {
    "threshold_days": 7,
    "critical_days": 3,
    "price_increase_pct": 15,
    "critical_increase_pct": 30,
    "max_price_increase_pct": 50,
    "min_margin_pct": 5,
    "use_7d_velocity": True,
    "exclude_zero_stock": True,
}


@register_strategy
class OutOfStockHandler(BaseStrategyHandler):
    strategy_type = "out_of_stock"

    async def execute(
        self,
        strategy: Strategy,
        config: dict,
        product_ids: list[int],
        db: AsyncSession,
    ) -> list[PriceRecommendation]:
        cfg = {**DEFAULT_CONFIG, **config}
        threshold_days = cfg["threshold_days"]
        critical_days = cfg["critical_days"]
        price_increase_pct = cfg["price_increase_pct"]
        critical_increase_pct = cfg["critical_increase_pct"]
        max_price_increase_pct = cfg["max_price_increase_pct"]
        min_margin_pct = cfg["min_margin_pct"]
        exclude_zero_stock = cfg["exclude_zero_stock"]

        # Load products
        result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = list(result.scalars().all())
        if not products:
            return []

        # Latest price per product (same pattern as _enrich_with_prices)
        latest_prices_q = (
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id.in_(product_ids))
            .distinct(PriceSnapshot.product_id)
            .order_by(PriceSnapshot.product_id, PriceSnapshot.collected_at.desc())
        )
        price_result = await db.execute(latest_prices_q)
        snapshots = {s.product_id: s for s in price_result.scalars().all()}

        # Orders for last 7 days (net of returns)
        today_msk = datetime.now(MSK).date()
        seven_days_ago = today_msk - timedelta(days=7)
        orders_q = (
            select(
                SalesDaily.product_id,
                func.sum(SalesDaily.orders_count),
                func.sum(SalesDaily.returns_count),
            )
            .where(
                SalesDaily.product_id.in_(product_ids),
                SalesDaily.date >= seven_days_ago,
                SalesDaily.date < today_msk,
            )
            .group_by(SalesDaily.product_id)
        )
        orders_result = await db.execute(orders_q)
        orders_map: dict[int, int] = {}
        for row in orders_result.all():
            net = max((row[1] or 0) - (row[2] or 0), 0)
            orders_map[row[0]] = net

        # Account settings for margin calc
        account_ids = {p.account_id for p in products}
        account_settings: dict[int, tuple[float, float]] = {}
        if account_ids:
            acc_result = await db.execute(
                select(WBAccount.id, WBAccount.tax_rate, WBAccount.tariff_rate).where(
                    WBAccount.id.in_(account_ids)
                )
            )
            for row in acc_result.all():
                tax = float(row[1]) if row[1] else 0.0
                tariff = float(row[2]) if row[2] else 0.0
                account_settings[row[0]] = (tax, tariff)

        recommendations: list[PriceRecommendation] = []

        for product in products:
            stock = product.total_stock or 0

            if exclude_zero_stock and stock == 0:
                continue

            snap = snapshots.get(product.id)
            if not snap or not snap.final_price:
                continue
            current_price = float(snap.final_price)

            orders_7d = orders_map.get(product.id, 0)
            velocity_7d = orders_7d / 7.0 if orders_7d > 0 else 0

            if velocity_7d > 0:
                days_remaining = stock / velocity_7d
            else:
                days_remaining = None  # no sales → stock is safe

            # Determine alert level
            if days_remaining is None or days_remaining >= threshold_days:
                continue  # safe — no recommendation needed

            if days_remaining >= critical_days:
                alert_level = "warning"
                increase_pct = price_increase_pct
            else:
                alert_level = "critical"
                increase_pct = critical_increase_pct

            increase_pct = min(increase_pct, max_price_increase_pct)
            recommended_price = round(current_price * (1 + increase_pct / 100), 2)

            # Margin calculations
            acc_tax, acc_tariff = account_settings.get(product.account_id, (0.0, 0.0))
            current_margin_pct, _ = calculate_promo_margin(
                product, current_price, acc_tax, acc_tariff
            )
            new_margin_pct, new_margin_rub = calculate_promo_margin(
                product, recommended_price, acc_tax, acc_tariff
            )

            # Build reason
            reason_parts = [
                f"Остаток {stock} шт, скорость {velocity_7d:.1f} шт/день, "
                f"хватит на {days_remaining:.1f} дней",
            ]
            if alert_level == "critical":
                reason_parts.append(f"КРИТИЧНО: < {critical_days} дней остатка")
            else:
                reason_parts.append(f"Предупреждение: < {threshold_days} дней остатка")
            reason_parts.append(f"Рекомендация: +{increase_pct}% к цене")

            if current_margin_pct is not None and current_margin_pct < min_margin_pct:
                reason_parts.append(
                    f"Внимание: текущая маржа ({current_margin_pct}%) ниже порога ({min_margin_pct}%)"
                )

            recommendations.append(
                PriceRecommendation(
                    product_id=product.id,
                    current_price=current_price,
                    recommended_price=recommended_price,
                    price_change_pct=round(increase_pct, 1),
                    current_margin_pct=current_margin_pct,
                    new_margin_pct=new_margin_pct,
                    new_margin_rub=new_margin_rub,
                    alert_level=alert_level,
                    reason=". ".join(reason_parts),
                    extra_data={
                        "total_stock": stock,
                        "orders_7d": orders_7d,
                        "velocity_7d": round(velocity_7d, 2),
                        "days_remaining": round(days_remaining, 1),
                    },
                )
            )

        logger.info(
            "Out-of-stock strategy %d: %d products, %d recommendations",
            strategy.id,
            len(products),
            len(recommendations),
        )
        return recommendations
