"""Promotion Collector: sync promotions and calculate promo margins."""

import asyncio
import json as json_module
import logging
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, WBAccount
from app.models.promotion import Promotion, PromotionProduct
from app.schemas.product import ExtraCostItem
from app.services.wb_api.client import WBApiClient

logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))


def _parse_wb_datetime(dt_str: str | None) -> date | None:
    """Parse WB datetime string (ISO format) to date."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(MSK).date()
    except (ValueError, AttributeError):
        return None


def _determine_status(start_date: date | None, end_date: date | None) -> str:
    """Determine promotion status based on dates."""
    today = datetime.now(MSK).date()
    if end_date and end_date < today:
        return "ended"
    if start_date and start_date > today:
        return "upcoming"
    return "active"


def calculate_promo_margin(
    product: Product,
    price: float,
    account_tax: float,
    account_tariff: float,
) -> tuple[float | None, float | None]:
    """Calculate margin for a given price using the same formula as _enrich_with_prices.

    Args:
        product: Product with cost_price, commission_pct, logistics_cost, etc.
        price: The price to calculate margin for (final_price or plan_price)
        account_tax: Account tax rate %
        account_tariff: Account tariff rate %

    Returns: (margin_pct, margin_rub) or (None, None) if calculation impossible.
    """
    cost_price = float(product.cost_price) if product.cost_price is not None else None
    if not price or not cost_price or price <= 0:
        return None, None

    commission_pct = float(product.commission_pct) if product.commission_pct is not None else None
    logistics_cost = float(product.logistics_cost) if product.logistics_cost is not None else None
    storage_cost = float(product.storage_cost) if product.storage_cost is not None else None
    ad_pct = float(product.ad_pct) if product.ad_pct is not None else None
    spp_pct = float(product.spp_pct) if product.spp_pct is not None else None

    # Parse extra costs
    extra_costs_total = 0.0
    if product.extra_costs_json:
        try:
            raw = json_module.loads(product.extra_costs_json)
            items = [ExtraCostItem(**item) for item in raw]
            extra_costs_total = sum(item.value for item in items if item.type == "fixed")
        except (json_module.JSONDecodeError, TypeError):
            pass

    # Tax is calculated from spp_price (buyer's actual price)
    spp_price = price * (1 - spp_pct / 100) if spp_pct else price
    tax_amount = spp_price * account_tax / 100 if account_tax else 0
    commission_amount = price * commission_pct / 100 if commission_pct else 0
    tariff_amount = price * account_tariff / 100 if account_tariff else 0
    ad_amount = price * ad_pct / 100 if ad_pct else 0

    total_costs = (
        cost_price
        + tax_amount
        + commission_amount
        + tariff_amount
        + (logistics_cost or 0)
        + (storage_cost or 0)
        + ad_amount
        + extra_costs_total
    )
    margin_rub = round(price - total_costs, 2)
    margin_pct = round(margin_rub / price * 100, 1)

    return margin_pct, margin_rub


async def sync_promotions(
    db: AsyncSession, client: WBApiClient, account_id: int
) -> int:
    """Sync promotions list from WB Calendar API.

    Returns number of promotions synced.
    """
    try:
        promos = await client.get_promotions()
    except Exception as e:
        logger.warning("Failed to fetch promotions: %s", e)
        return 0

    if not promos:
        logger.info("No promotions from WB for account %d", account_id)
        return 0

    now = datetime.now(UTC)
    synced = 0
    skipped = 0

    for p in promos:
        wb_id = str(p.get("id", ""))
        if not wb_id:
            continue

        name = p.get("name", "Unknown promotion")
        start_date = _parse_wb_datetime(p.get("startDateTime"))
        end_date = _parse_wb_datetime(p.get("endDateTime"))
        promo_type = p.get("type", "regular")
        in_action_count = p.get("inPromoActionLeftCount", 0) or 0
        total_available = p.get("inPromoActionTotalCount", 0) or 0
        status = _determine_status(start_date, end_date)

        # Skip promotions where none of our products can participate
        if total_available == 0 and in_action_count == 0:
            skipped += 1
            continue

        # Upsert by wb_promo_id
        result = await db.execute(
            select(Promotion).where(Promotion.wb_promo_id == wb_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = name
            existing.start_date = start_date
            existing.end_date = end_date
            existing.promo_type = promo_type
            existing.status = status
            existing.in_action_count = in_action_count
            existing.total_available = total_available
            existing.updated_at = now
        else:
            db.add(Promotion(
                account_id=account_id,
                wb_promo_id=wb_id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                promo_type=promo_type,
                status=status,
                in_action_count=in_action_count,
                total_available=total_available,
                is_active=status != "ended",
                created_at=now,
                updated_at=now,
            ))
        synced += 1

    await db.flush()
    logger.info(
        "Synced %d promotions for account %d (skipped %d with no eligible products, %d total from API)",
        synced, account_id, skipped, len(promos),
    )
    return synced


async def sync_promotion_products(
    db: AsyncSession,
    client: WBApiClient,
    account_id: int,
    promotion_db_id: int,
    wb_promo_id: str,
) -> int:
    """Sync promotion nomenclatures and calculate margins.

    Args:
        db: Database session
        client: WB API client
        account_id: WB account ID
        promotion_db_id: Our DB promotion.id
        wb_promo_id: WB promotion ID (for API call)

    Returns number of products synced.
    """
    # Rate limit: 10 requests per 6 seconds — wait before each promotion
    await asyncio.sleep(1.5)
    try:
        nomenclatures = await client.get_promotion_nomenclatures(int(wb_promo_id))
    except Exception as e:
        logger.warning("Failed to fetch nomenclatures for promotion %s: %s", wb_promo_id, e)
        return 0

    if not nomenclatures:
        logger.info("No nomenclatures for promotion %s", wb_promo_id)
        return 0

    # Load products for this account (for margin calculation)
    result = await db.execute(
        select(Product).where(Product.account_id == account_id)
    )
    products = list(result.scalars().all())
    nm_to_product = {p.nm_id: p for p in products}

    # Load account settings (tax, tariff)
    acc_result = await db.execute(
        select(WBAccount).where(WBAccount.id == account_id)
    )
    account = acc_result.scalar_one_or_none()
    account_tax = float(account.tax_rate) if account and account.tax_rate else 0.0
    account_tariff = float(account.tariff_rate) if account and account.tariff_rate else 0.0

    # Build existing promotion_products map for upsert
    existing_result = await db.execute(
        select(PromotionProduct).where(
            PromotionProduct.promotion_id == promotion_db_id
        )
    )
    existing_map = {pp.nm_id: pp for pp in existing_result.scalars().all()}

    synced = 0
    for item in nomenclatures:
        nm_id = item.get("nmID")
        if not nm_id:
            continue

        plan_price = item.get("planPrice")
        plan_discount = item.get("planDiscount")
        current_price = item.get("currentPrice")
        in_action = item.get("inAction", False)

        # Calculate margins if we have this product
        product = nm_to_product.get(nm_id)
        current_margin_pct = None
        current_margin_rub = None
        promo_margin_pct = None
        promo_margin_rub = None

        if product:
            # Current margin (using current final_price from our data)
            if current_price:
                current_margin_pct, current_margin_rub = calculate_promo_margin(
                    product, float(current_price), account_tax, account_tariff
                )
            # Promo margin (using plan_price — max allowed promo price)
            if plan_price:
                promo_margin_pct, promo_margin_rub = calculate_promo_margin(
                    product, float(plan_price), account_tax, account_tariff
                )

        # Upsert
        existing_pp = existing_map.get(nm_id)
        if existing_pp:
            existing_pp.plan_price = plan_price
            existing_pp.plan_discount = plan_discount
            existing_pp.current_price = current_price
            existing_pp.in_action = in_action
            existing_pp.promo_price = plan_price
            existing_pp.current_margin_pct = current_margin_pct
            existing_pp.current_margin_rub = current_margin_rub
            existing_pp.promo_margin_pct = promo_margin_pct
            existing_pp.promo_margin_rub = promo_margin_rub
        else:
            db.add(PromotionProduct(
                promotion_id=promotion_db_id,
                account_id=account_id,
                nm_id=nm_id,
                plan_price=plan_price,
                plan_discount=plan_discount,
                current_price=current_price,
                in_action=in_action,
                promo_price=plan_price,
                current_margin_pct=current_margin_pct,
                current_margin_rub=current_margin_rub,
                promo_margin_pct=promo_margin_pct,
                promo_margin_rub=promo_margin_rub,
                decision="pending",
            ))
        synced += 1

    await db.flush()
    logger.info(
        "Synced %d promotion products for promotion %s (account %d)",
        synced, wb_promo_id, account_id,
    )
    return synced
