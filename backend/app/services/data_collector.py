"""Data Collector: sync products and prices from WB API into the database."""

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import decrypt_api_key
from app.models.price import PriceSnapshot
from app.models.product import Product, WBAccount
from app.models.sales import SalesDaily
from app.services.wb_api.client import WBApiClient

logger = logging.getLogger(__name__)


async def _get_active_accounts(db: AsyncSession) -> list[WBAccount]:
    """Get all active WB accounts."""
    result = await db.execute(
        select(WBAccount).where(WBAccount.is_active == True)  # noqa: E712
    )
    return list(result.scalars().all())


async def sync_products(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync product cards from WB Content API into Products table.

    Returns number of products synced.
    """
    cards = await client.get_products()
    synced = 0

    for card in cards:
        nm_id = card.get("nmID")
        if not nm_id:
            continue

        # Check if product already exists
        result = await db.execute(
            select(Product).where(Product.nm_id == nm_id)
        )
        product = result.scalar_one_or_none()

        # Build photo URL from WB CDN
        photos = card.get("photos", [])
        image_url = photos[0].get("big") if photos else None

        # Extract first barcode from sizes
        sizes = card.get("sizes", [])
        barcode = None
        if sizes:
            skus = sizes[0].get("skus", [])
            if skus:
                barcode = skus[0]

        if product:
            # Update existing product
            product.title = card.get("title") or product.title
            product.brand = card.get("brand") or product.brand
            product.vendor_code = card.get("vendorCode") or product.vendor_code
            product.category = card.get("subjectName") or product.category
            if image_url:
                product.image_url = image_url
            if barcode:
                product.barcode = barcode
        else:
            # Create new product
            product = Product(
                account_id=account_id,
                nm_id=nm_id,
                vendor_code=card.get("vendorCode"),
                brand=card.get("brand"),
                category=card.get("subjectName"),
                title=card.get("title"),
                image_url=image_url,
                barcode=barcode,
                is_active=True,
            )
            db.add(product)

        synced += 1

    await db.flush()
    logger.info("Synced %d products for account %d", synced, account_id)
    return synced


async def sync_prices(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync prices from WB Prices API, save PriceSnapshots.

    Returns number of price snapshots created.
    """
    goods = await client.get_prices()
    now = datetime.now(UTC)
    snapshots_count = 0

    # Build nm_id → product_id map for this account
    result = await db.execute(
        select(Product.nm_id, Product.id).where(Product.account_id == account_id)
    )
    product_map = {row.nm_id: row.id for row in result.all()}

    for item in goods:
        nm_id = item.get("nmID")
        if not nm_id or nm_id not in product_map:
            continue

        product_id = product_map[nm_id]

        # Each good can have multiple sizes; take the first one for price info
        sizes = item.get("sizes", [])
        if not sizes:
            continue

        size = sizes[0]
        price = size.get("price", 0)
        discounted_price = size.get("discountedPrice", 0)

        # Calculate discount percentage
        discount_pct = 0.0
        if price > 0:
            discount_pct = round((1 - discounted_price / price) * 100, 2)

        snapshot = PriceSnapshot(
            product_id=product_id,
            wb_price=price,
            wb_discount=discount_pct,
            final_price=discounted_price,
            source="api",
            collected_at=now,
        )
        db.add(snapshot)
        snapshots_count += 1

    await db.flush()
    logger.info("Created %d price snapshots for account %d", snapshots_count, account_id)
    return snapshots_count


async def sync_stocks(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync stock quantities from WB Statistics API into Product.total_stock.

    Uses Statistics API /supplier/stocks which covers both FBO and FBS warehouses.
    Returns number of products with updated stock.
    """
    # Get products for this account
    result = await db.execute(
        select(Product).where(Product.account_id == account_id)
    )
    products = list(result.scalars().all())
    if not products:
        logger.info("No products for account %d", account_id)
        return 0

    nm_to_product = {p.nm_id: p for p in products}

    try:
        stock_map = await client.get_supplier_stocks()
    except Exception as e:
        logger.warning("Failed to fetch stocks: %s", e)
        return 0

    updated = 0
    for nm_id, qty in stock_map.items():
        product = nm_to_product.get(nm_id)
        if product and product.total_stock != qty:
            product.total_stock = qty
            updated += 1

    # Set stock to 0 for products not in stock_map
    for nm_id, product in nm_to_product.items():
        if nm_id not in stock_map and product.total_stock != 0:
            product.total_stock = 0
            updated += 1

    await db.flush()
    logger.info("Updated stock for %d products (account %d)", updated, account_id)
    return updated


async def sync_orders(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync orders and returns from WB Statistics API into SalesDaily.

    Fetches last 7 days of orders and sales (returns), aggregates by (nm_id, date MSK),
    upserts into sales_daily. Returns number of daily records upserted.
    """
    # WB works in Moscow timezone (UTC+3)
    MSK = timezone(timedelta(hours=3))
    now_msk = datetime.now(MSK)
    date_from = (now_msk - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")

    # Build nm_id → product_id map
    result = await db.execute(
        select(Product.nm_id, Product.id).where(Product.account_id == account_id)
    )
    product_map = {row.nm_id: row.id for row in result.all()}

    # --- Fetch orders ---
    try:
        orders = await client.get_orders(date_from)
    except Exception as e:
        logger.warning("Failed to fetch orders: %s", e)
        orders = []

    def _parse_date_msk(date_str: str) -> date | None:
        """Parse WB date string and convert to Moscow date."""
        if not date_str:
            return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.astimezone(MSK).date()
        except (ValueError, AttributeError):
            return None

    # Aggregate orders by (nm_id, date MSK), excluding cancelled
    daily_orders: dict[tuple[int, date], int] = defaultdict(int)
    for order in orders:
        if order.get("isCancel"):
            continue
        nm_id = order.get("nmId")
        if not nm_id or nm_id not in product_map:
            continue
        order_date = _parse_date_msk(order.get("date", ""))
        if not order_date:
            continue
        daily_orders[(nm_id, order_date)] += 1

    # --- Fetch sales/returns ---
    try:
        sales = await client.get_sales(date_from)
    except Exception as e:
        logger.warning("Failed to fetch sales: %s", e)
        sales = []

    # Count returns by (nm_id, date MSK)
    daily_returns: dict[tuple[int, date], int] = defaultdict(int)
    for sale in sales:
        if not sale.get("isReturn"):
            continue
        nm_id = sale.get("nmId")
        if not nm_id or nm_id not in product_map:
            continue
        sale_date = _parse_date_msk(sale.get("date", ""))
        if not sale_date:
            continue
        daily_returns[(nm_id, sale_date)] += 1

    # --- Upsert into sales_daily ---
    all_keys = set(daily_orders.keys()) | set(daily_returns.keys())
    upserted = 0
    for key in all_keys:
        nm_id, order_date = key
        product_id = product_map[nm_id]
        orders_count = daily_orders.get(key, 0)
        returns_count = daily_returns.get(key, 0)

        result = await db.execute(
            select(SalesDaily).where(
                SalesDaily.product_id == product_id,
                SalesDaily.date == order_date,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.orders_count = orders_count
            existing.returns_count = returns_count
        else:
            db.add(SalesDaily(
                product_id=product_id,
                date=order_date,
                orders_count=orders_count,
                returns_count=returns_count,
            ))
        upserted += 1

    await db.flush()
    logger.info(
        "Upserted %d daily records for account %d (orders from %d items, returns from %d items)",
        upserted, account_id, len(orders), len(sales),
    )
    return upserted


async def sync_tariffs(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync WB commission rates by product category.

    Fetches commission rates from WB Common API (public, no auth)
    and updates commission_pct for each product based on its category.
    Returns number of products with updated commission.
    """
    # Fetch commission rates by category
    try:
        commissions = await client.get_commissions()
    except Exception as e:
        logger.warning("Failed to fetch commissions: %s", e)
        return 0

    if not commissions:
        logger.info("No commission data received")
        return 0

    # Get products for this account
    result = await db.execute(
        select(Product).where(Product.account_id == account_id)
    )
    products = list(result.scalars().all())

    updated = 0
    for product in products:
        if not product.category:
            continue
        commission = commissions.get(product.category)
        if commission is not None:
            new_val = round(commission, 2)
            if product.commission_pct != new_val:
                product.commission_pct = new_val
                updated += 1

    await db.flush()
    logger.info("Updated commission for %d products (account %d)", updated, account_id)
    return updated


async def sync_financial_costs(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync per-unit logistics and SPP from WB financial report.

    Fetches reportDetailByPeriod for last 4 weeks and calculates:
    - logistics_cost: total logistics (forward + return) / sales count — effective per-sale cost
    - spp_pct: average SPP % from sales
    Note: storage is handled separately via sync_paid_storage() — WB reports storage with nm_id=0 here.
    Returns number of products updated.
    """
    MSK = timezone(timedelta(hours=3))
    now_msk = datetime.now(MSK)
    date_from = (now_msk - timedelta(days=28)).strftime("%Y-%m-%d")
    date_to = now_msk.strftime("%Y-%m-%d")

    try:
        rows = await client.get_report_detail(date_from, date_to)
    except Exception as e:
        logger.warning("Failed to fetch financial report: %s", e)
        return 0

    if not rows:
        logger.info("No financial report data for account %d", account_id)
        return 0

    # Aggregate by nm_id
    seen_in_report: set[int] = set()                          # nm_ids with any report data
    logistics_total: dict[int, float] = defaultdict(float)   # SUM(delivery_rub) — all logistics including returns
    sales_count: dict[int, int] = defaultdict(int)            # count of sales (denominator for logistics)
    spp_values: dict[int, list[float]] = defaultdict(list)    # ppvz_spp_prc per sale

    for row in rows:
        nm_id = row.get("nm_id")
        if not nm_id:
            continue

        seen_in_report.add(nm_id)

        delivery_rub = row.get("delivery_rub", 0) or 0
        oper_name = row.get("supplier_oper_name", "")
        quantity = row.get("quantity", 0) or 0
        spp_prc = row.get("ppvz_spp_prc")

        # Sum ALL delivery costs (forward + return logistics + corrections)
        logistics_total[nm_id] += delivery_rub
        if oper_name == "Продажа" and quantity > 0:
            sales_count[nm_id] += quantity
            if spp_prc is not None:
                spp_values[nm_id].append(float(spp_prc))

    # Get products for this account
    result = await db.execute(
        select(Product).where(Product.account_id == account_id)
    )
    products = list(result.scalars().all())
    nm_to_product = {p.nm_id: p for p in products}

    updated = 0
    for nm_id, product in nm_to_product.items():
        if nm_id not in seen_in_report:
            continue
        changed = False

        # Logistics per sale (total logistics including return overhead / sales count)
        if sales_count.get(nm_id, 0) > 0:
            new_logistics = round(logistics_total.get(nm_id, 0) / sales_count[nm_id], 2)
            if product.logistics_cost != new_logistics:
                product.logistics_cost = new_logistics
                changed = True

        # Average SPP % from sales
        if nm_id in spp_values and spp_values[nm_id]:
            avg_spp = round(sum(spp_values[nm_id]) / len(spp_values[nm_id]), 1)
            if product.spp_pct != avg_spp:
                product.spp_pct = avg_spp
                changed = True

        if changed:
            updated += 1

    await db.flush()
    logger.info(
        "Updated financial costs for %d products (account %d, %d report rows)",
        updated, account_id, len(rows),
    )
    return updated


async def sync_paid_storage(db: AsyncSession, client: WBApiClient, account_id: int) -> int:
    """Sync per-product storage costs from WB paid storage API.

    Uses task-based /api/v1/paid_storage (max 8 days per request).
    Fetches last 28 days in 8-day chunks.
    Calculates:
    - storage_daily: average daily storage cost (SUM(warehousePrice) / days_in_period)
    - storage_cost: storage per unit (SUM(warehousePrice) / total_stock)
    Returns number of products updated.
    """
    MSK = timezone(timedelta(hours=3))
    now_msk = datetime.now(MSK)
    period_days = 28
    chunk_days = 8

    # Fetch in 8-day chunks (WB max period per request)
    entries: list[dict] = []
    chunk_start = now_msk - timedelta(days=period_days)
    while chunk_start < now_msk:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), now_msk)
        date_from = chunk_start.strftime("%Y-%m-%d")
        date_to = chunk_end.strftime("%Y-%m-%d")
        try:
            chunk_entries = await client.get_paid_storage(date_from, date_to)
            entries.extend(chunk_entries)
        except Exception as e:
            logger.warning("Failed to fetch paid storage for %s — %s: %s", date_from, date_to, e)
        chunk_start = chunk_end

    if not entries:
        logger.info("No paid storage data for account %d", account_id)
        return 0

    # Aggregate warehousePrice per nm_id
    storage_by_nm: dict[int, float] = defaultdict(float)
    for entry in entries:
        nm_id = entry.get("nmId")
        if not nm_id:
            continue
        price = entry.get("warehousePrice", 0) or 0
        storage_by_nm[nm_id] += price

    days_in_period = period_days

    # Get products for this account
    result = await db.execute(
        select(Product).where(Product.account_id == account_id)
    )
    products = list(result.scalars().all())
    nm_to_product = {p.nm_id: p for p in products}

    updated = 0
    for nm_id, product in nm_to_product.items():
        total_storage = storage_by_nm.get(nm_id, 0)
        changed = False

        # Storage daily total
        new_storage_daily = round(total_storage / days_in_period, 2)
        if product.storage_daily != new_storage_daily:
            product.storage_daily = new_storage_daily
            changed = True

        # Storage per sale — need sales_count; fallback to daily if no sales
        # Use a simple heuristic: if we have orders_7d, extrapolate to 28d
        # For accurate per-sale: this will be refined when financial report data is available
        new_storage_per_sale = new_storage_daily  # default to daily cost
        if product.storage_daily is not None and total_storage > 0:
            # Try to calculate per-sale from total_stock turnover
            # Simple approach: storage per unit = total_storage / total_stock (if in stock)
            if product.total_stock and product.total_stock > 0:
                new_storage_per_sale = round(total_storage / product.total_stock, 2)
            else:
                new_storage_per_sale = new_storage_daily

        if product.storage_cost != new_storage_per_sale:
            product.storage_cost = new_storage_per_sale
            changed = True

        if changed:
            updated += 1

    await db.flush()
    logger.info(
        "Updated paid storage for %d products (account %d, %d entries)",
        updated, account_id, len(entries),
    )
    return updated


async def collect_all() -> dict:
    """Main entry point: collect products, prices and stocks for all active WB accounts.

    Returns summary of what was collected.
    """
    results = {
        "accounts": 0,
        "products_synced": 0,
        "price_snapshots": 0,
        "stocks_updated": 0,
        "orders_synced": 0,
        "commissions_updated": 0,
        "financial_costs_updated": 0,
        "storage_updated": 0,
        "promotions_synced": 0,
        "errors": [],
    }

    async with async_session() as db:
        accounts = await _get_active_accounts(db)
        results["accounts"] = len(accounts)

        if not accounts:
            logger.warning("No active WB accounts found")
            return results

        for account in accounts:
            try:
                api_key = decrypt_api_key(account.api_key_encrypted)
                client = WBApiClient(api_key)

                products_count = await sync_products(db, client, account.id)
                results["products_synced"] += products_count

                prices_count = await sync_prices(db, client, account.id)
                results["price_snapshots"] += prices_count

                stocks_count = await sync_stocks(db, client, account.id)
                results["stocks_updated"] += stocks_count

                orders_count = await sync_orders(db, client, account.id)
                results["orders_synced"] += orders_count

                commissions_count = await sync_tariffs(db, client, account.id)
                results["commissions_updated"] += commissions_count

                financial_count = await sync_financial_costs(db, client, account.id)
                results["financial_costs_updated"] += financial_count

                storage_count = await sync_paid_storage(db, client, account.id)
                results["storage_updated"] += storage_count

                # Note: Promotions are imported via Excel upload (POST /promotions/import)
                # WB Calendar API requires permissions not available in standard API keys

            except Exception as e:
                error_msg = f"Account {account.id} ({account.name}): {e}"
                logger.error("Data collection failed: %s", error_msg)
                results["errors"].append(error_msg)

        await db.commit()

    logger.info(
        "Data collection complete: %d accounts, %d products, %d prices, %d stocks, %d orders, %d commissions, %d financial",
        results["accounts"],
        results["products_synced"],
        results["price_snapshots"],
        results["stocks_updated"],
        results["orders_synced"],
        results["commissions_updated"],
        results["financial_costs_updated"],
    )
    return results
