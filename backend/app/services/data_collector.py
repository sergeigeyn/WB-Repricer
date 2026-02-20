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

            except Exception as e:
                error_msg = f"Account {account.id} ({account.name}): {e}"
                logger.error("Data collection failed: %s", error_msg)
                results["errors"].append(error_msg)

        await db.commit()

    logger.info(
        "Data collection complete: %d accounts, %d products, %d prices, %d stocks, %d orders",
        results["accounts"],
        results["products_synced"],
        results["price_snapshots"],
        results["stocks_updated"],
        results["orders_synced"],
    )
    return results
