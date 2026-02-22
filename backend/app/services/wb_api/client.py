"""WB API client abstraction layer.

WB uses different domains per API section:
- content-api.wildberries.ru — product cards
- discounts-prices-api.wildberries.ru — prices & discounts
- statistics-api.wildberries.ru — orders & sales history
- marketplace-api.wildberries.ru — FBO/FBS orders, stocks, warehouses
- advert-api.wildberries.ru — advertising campaigns
- dp-calendar-api.wildberries.ru — promotions calendar
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# WB API domain mapping
WB_CONTENT = "https://content-api.wildberries.ru"
WB_PRICES = "https://discounts-prices-api.wildberries.ru"
WB_STATISTICS = "https://statistics-api.wildberries.ru"
WB_MARKETPLACE = "https://marketplace-api.wildberries.ru"
WB_ADVERT = "https://advert-api.wildberries.ru"
WB_COMMON = "https://common-api.wildberries.ru"
WB_ANALYTICS = "https://seller-analytics-api.wildberries.ru"
WB_CALENDAR = "https://dp-calendar-api.wildberries.ru"


class BaseWBClient(ABC):
    """Abstract WB API client interface."""

    @abstractmethod
    async def get_products(self) -> list[dict[str, Any]]:
        """Get list of products from WB cabinet."""

    @abstractmethod
    async def get_prices(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get current prices and discounts."""

    @abstractmethod
    async def get_orders(self, date_from: str) -> list[dict[str, Any]]:
        """Get orders from date."""

    @abstractmethod
    async def get_sales(self, date_from: str) -> list[dict[str, Any]]:
        """Get sales from date."""


class WBApiClient(BaseWBClient):
    """Real WB API client using per-domain HTTP requests."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": api_key}
        self.timeout = 30.0

    async def _request_with_timeout(self, timeout: float, method: str, url: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return []
            return response.json()

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return []
            return response.json()

    async def get_products(self) -> list[dict[str, Any]]:
        """Fetch all product cards via Content API with cursor pagination."""
        all_cards: list[dict[str, Any]] = []
        # First request: no updatedAt/nmID (WB rejects empty string for updatedAt)
        cursor: dict[str, Any] = {"limit": 100}

        while True:
            data = await self._request(
                "POST",
                f"{WB_CONTENT}/content/v2/get/cards/list",
                json={
                    "settings": {
                        "cursor": cursor,
                        "filter": {"withPhoto": -1},
                    }
                },
            )
            cards = data.get("cards", [])
            all_cards.extend(cards)

            new_cursor = data.get("cursor", {})
            total = new_cursor.get("total", 0)
            if not cards or len(all_cards) >= total:
                break
            # For subsequent pages, include cursor fields from response
            cursor = {
                "limit": 100,
                "updatedAt": new_cursor.get("updatedAt", ""),
                "nmID": new_cursor.get("nmID", 0),
            }

        logger.info("Fetched %d product cards from WB", len(all_cards))
        return all_cards

    async def get_prices(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch prices via Discounts-Prices API with pagination."""
        all_goods: list[dict[str, Any]] = []
        offset = 0

        while True:
            data = await self._request(
                "GET",
                f"{WB_PRICES}/api/v2/list/goods/filter?limit={limit}&offset={offset}",
            )
            goods = data.get("data", {}).get("listGoods", [])
            all_goods.extend(goods)

            if len(goods) < limit:
                break
            offset += limit

        logger.info("Fetched prices for %d goods from WB", len(all_goods))
        return all_goods

    async def get_warehouses(self) -> list[dict[str, Any]]:
        """Fetch seller's FBS warehouses."""
        data = await self._request(
            "GET", f"{WB_MARKETPLACE}/api/v3/warehouses"
        )
        return data if isinstance(data, list) else []

    async def get_supplier_stocks(self) -> dict[int, int]:
        """Fetch stock quantities from Statistics API (covers FBO + FBS warehouses).

        Returns: {nm_id: total_quantity} aggregated across all warehouses.
        """
        # Statistics API requires dateFrom, use 1 day ago
        from datetime import datetime, timedelta, UTC
        date_from = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

        data = await self._request(
            "GET",
            f"{WB_STATISTICS}/api/v1/supplier/stocks?dateFrom={date_from}",
        )
        items = data if isinstance(data, list) else []

        # Aggregate quantity by nmId across all warehouses
        stock_map: dict[int, int] = {}
        for item in items:
            nm_id = item.get("nmId")
            qty = item.get("quantity", 0)
            if nm_id:
                stock_map[nm_id] = stock_map.get(nm_id, 0) + qty

        logger.info("Fetched stocks for %d products via Statistics API", len(stock_map))
        return stock_map

    async def get_orders(self, date_from: str) -> list[dict[str, Any]]:
        """Fetch orders via Statistics API."""
        data = await self._request(
            "GET",
            f"{WB_STATISTICS}/api/v1/supplier/orders?dateFrom={date_from}",
        )
        orders = data if isinstance(data, list) else []
        logger.info("Fetched %d orders from WB", len(orders))
        return orders

    async def get_sales(self, date_from: str) -> list[dict[str, Any]]:
        """Fetch sales via Statistics API."""
        data = await self._request(
            "GET",
            f"{WB_STATISTICS}/api/v1/supplier/sales?dateFrom={date_from}",
        )
        sales = data if isinstance(data, list) else []
        logger.info("Fetched %d sales from WB", len(sales))
        return sales

    async def get_report_detail(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Fetch detailed financial report (reportDetailByPeriod) via Statistics API v5.

        Includes delivery_rub, storage_fee, commission per operation.
        Uses rrdid-based pagination (up to 100K rows per page).

        Args:
            date_from: Start date YYYY-MM-DD
            date_to: End date YYYY-MM-DD

        Returns: list of report rows (each row is a dict with nm_id, delivery_rub, etc.)
        """
        all_rows: list[dict[str, Any]] = []
        rrdid = 0

        while True:
            data = await self._request_with_timeout(
                60.0,
                "GET",
                f"{WB_STATISTICS}/api/v5/supplier/reportDetailByPeriod",
                params={
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "limit": 100000,
                    "rrdid": rrdid,
                },
            )
            rows = data if isinstance(data, list) else []
            if not rows:
                break
            all_rows.extend(rows)
            rrdid = rows[-1].get("rrd_id", 0)

        logger.info("Fetched %d report rows from WB (period %s — %s)", len(all_rows), date_from, date_to)
        return all_rows

    async def get_commissions(self) -> dict[str, float]:
        """Fetch WB commission rates by product category.

        Returns: {subject_name: commission_pct} where commission_pct is
        the FBO marketplace commission (kgvpMarketplace).
        """
        data = await self._request(
            "GET", f"{WB_COMMON}/api/v1/tariffs/commission"
        )

        report = data.get("report", [])
        result: dict[str, float] = {}
        for item in report:
            name = item.get("subjectName", "")
            commission = item.get("kgvpMarketplace", 0)
            if name:
                result[name] = commission

        logger.info("Fetched commission rates for %d categories", len(result))
        return result

    async def get_paid_storage(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Fetch paid storage data via async task-based API.

        WB paid storage API works in 3 steps:
        1. Create task (GET /api/v1/paid_storage?dateFrom=...&dateTo=...) → taskId
        2. Poll status (GET /api/v1/paid_storage/tasks/{taskId}/status) until "done"
        3. Download results (GET /api/v1/paid_storage/tasks/{taskId}/download)

        Max period: 8 days per request.

        Returns list of storage entries with nmId, warehousePrice, etc.
        """
        # Step 1: Create task
        data = await self._request(
            "GET",
            f"{WB_ANALYTICS}/api/v1/paid_storage",
            params={"dateFrom": date_from, "dateTo": date_to},
        )
        task_id = data.get("data", {}).get("taskId") if isinstance(data, dict) else None
        if not task_id:
            logger.warning("Paid storage: no taskId returned, response: %s", data)
            return []

        logger.info("Paid storage task created: %s (period %s — %s)", task_id, date_from, date_to)

        # Step 2: Poll status (max ~2 minutes, check every 10 seconds)
        for _ in range(12):
            await asyncio.sleep(10)
            status_data = await self._request(
                "GET",
                f"{WB_ANALYTICS}/api/v1/paid_storage/tasks/{task_id}/status",
            )
            status = status_data.get("data", {}).get("status", "") if isinstance(status_data, dict) else ""
            if status == "done":
                break
            if status in ("canceled", "purged"):
                logger.warning("Paid storage task %s has status: %s", task_id, status)
                return []
        else:
            logger.warning("Paid storage task %s timed out waiting for completion", task_id)
            return []

        # Step 3: Download results (with retry on 429)
        for attempt in range(3):
            try:
                items = await self._request_with_timeout(
                    120.0,
                    "GET",
                    f"{WB_ANALYTICS}/api/v1/paid_storage/tasks/{task_id}/download",
                )
                result = items if isinstance(items, list) else []
                logger.info("Fetched %d paid storage entries from WB (period %s — %s)", len(result), date_from, date_to)
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 2:
                    wait = 15 * (attempt + 1)
                    logger.warning("Paid storage download 429, retrying in %ds (attempt %d/3)", wait, attempt + 1)
                    await asyncio.sleep(wait)
                else:
                    raise
        return []

    async def get_box_tariffs(self) -> dict[str, Any]:
        """Fetch box delivery and storage tariffs.

        Returns tariff data including base delivery/storage costs and coefficients.
        """
        from datetime import date as date_type
        today = date_type.today().isoformat()

        data = await self._request(
            "GET", f"{WB_COMMON}/api/v1/tariffs/box",
            params={"date": today},
        )

        tariffs = data.get("response", {}).get("data", {}).get("warehouseList", [])
        logger.info("Fetched box tariffs for %d warehouses", len(tariffs))
        return data

    # --- Analytics API (Sales Funnel v3, replaces deprecated nm-report v2) ---

    async def get_sales_funnel_history(
        self, nm_ids: list[int], start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch daily card analytics via Sales Funnel v3 API.

        WB Analytics API returns views, cart adds, orders, buyouts, conversions per day per nmID.
        Rate limit: 3 requests per 20 seconds.
        Max period: 7 days per request.

        Args:
            nm_ids: list of nmID
            start_date: start date "YYYY-MM-DD"
            end_date: end date "YYYY-MM-DD"

        Returns: list of dicts with nmID and daily history data.
        """
        all_items: list[dict[str, Any]] = []

        # Split into 7-day chunks (WB max period per request)
        from datetime import datetime as dt_cls
        start = dt_cls.strptime(start_date, "%Y-%m-%d").date()
        end = dt_cls.strptime(end_date, "%Y-%m-%d").date()

        date_chunks: list[tuple[str, str]] = []
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=6), end)
            date_chunks.append((chunk_start.isoformat(), chunk_end.isoformat()))
            chunk_start = chunk_end + timedelta(days=1)

        for chunk_idx, (chunk_s, chunk_e) in enumerate(date_chunks):
            # Process in batches — no strict batch size limit in v3, but keep reasonable
            offset = 0
            while True:
                try:
                    data = await self._request(
                        "POST",
                        f"{WB_ANALYTICS}/api/analytics/v3/sales-funnel/products/history",
                        json={
                            "selectedPeriod": {"start": chunk_s, "end": chunk_e},
                            "nmIds": nm_ids,
                            "brandNames": [],
                            "subjectIds": [],
                            "tagIds": [],
                            "limit": 100,
                            "offset": offset,
                        },
                    )
                    items = data.get("data", []) if isinstance(data, dict) else []
                    all_items.extend(items)

                    # If fewer items than limit, no more pages
                    if len(items) < 100:
                        break
                    offset += 100
                except Exception as e:
                    logger.warning(
                        "sales-funnel history chunk %s-%s offset %d failed: %s",
                        chunk_s, chunk_e, offset, e,
                    )
                    break

                # Rate limit: 3 req / 20 sec — wait 7 sec between requests
                await asyncio.sleep(7)

            # Delay between date chunks
            if chunk_idx + 1 < len(date_chunks):
                await asyncio.sleep(7)

        logger.info(
            "Fetched sales-funnel history for %d products (%d date chunks)",
            len(nm_ids),
            len(date_chunks),
        )
        return all_items

    # --- Calendar API (Promotions) ---

    async def get_promotions(self) -> list[dict[str, Any]]:
        """Fetch list of available promotions from WB Calendar API.

        Requires params: allPromo, startDateTime, endDateTime (RFC3339).
        Returns list of promotions with id, name, dates, type, counts.
        """
        from datetime import datetime as dt, timedelta, timezone
        now = dt.now(timezone.utc)
        # Fetch promotions from 3 months ago to 3 months ahead
        start = (now - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")
        end = (now + timedelta(days=90)).strftime("%Y-%m-%dT23:59:59Z")

        data = await self._request(
            "GET", f"{WB_CALENDAR}/api/v1/calendar/promotions",
            params={
                "allPromo": "true",
                "startDateTime": start,
                "endDateTime": end,
                "limit": 1000,
                "offset": 0,
            },
        )
        promotions = data.get("data", {}).get("promotions", []) if isinstance(data, dict) else []
        logger.info("Fetched %d promotions from WB Calendar API", len(promotions))
        return promotions

    async def get_promotion_details(self, promo_id: int) -> dict[str, Any]:
        """Fetch promotion details (description, conditions).

        Args:
            promo_id: WB promotion ID

        Returns: promotion detail dict.
        """
        data = await self._request(
            "GET",
            f"{WB_CALENDAR}/api/v1/calendar/promotions/details",
            params={"promotionIDs": promo_id},
        )
        return data.get("data", {}).get("promotions", [{}])[0] if isinstance(data, dict) else {}

    async def get_promotion_nomenclatures(self, promo_id: int) -> list[dict[str, Any]]:
        """Fetch nomenclatures (products) eligible for a promotion.

        Fetches both inAction=true and inAction=false to get full picture.
        Returns list of dicts with nmID, planPrice, planDiscount, inAction, currentPrice.
        Uses limit/offset pagination (default 1000 per page).
        """
        all_items: list[dict[str, Any]] = []
        seen_nms: set[int] = set()

        for in_action_val in ["true", "false"]:
            offset = 0
            limit = 1000
            while True:
                try:
                    data = await self._request(
                        "GET",
                        f"{WB_CALENDAR}/api/v1/calendar/promotions/nomenclatures",
                        params={"promotionID": promo_id, "inAction": in_action_val, "limit": limit, "offset": offset},
                    )
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 422:
                        # Some promotions don't support nomenclature queries
                        break
                    raise
                items = data.get("data", {}).get("nomenclatures", []) if isinstance(data, dict) else []
                for item in items:
                    nm = item.get("nmID")
                    if nm and nm not in seen_nms:
                        seen_nms.add(nm)
                        all_items.append(item)

                if len(items) < limit:
                    break
                offset += limit

        logger.info("Fetched %d nomenclatures for promotion %d", len(all_items), promo_id)
        return all_items

    async def upload_promotion_nomenclatures(
        self, promo_id: int, nomenclatures: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Enter products into a promotion via WB Calendar API.

        Args:
            promo_id: WB promotion ID
            nomenclatures: list of {"nm": nmID, "newPrice": price}

        Returns: API response dict.
        """
        data = await self._request(
            "POST",
            f"{WB_CALENDAR}/api/v1/calendar/promotions/nomenclatures",
            json={
                "data": {
                    "promotionID": promo_id,
                    "nomenclatures": nomenclatures,
                }
            },
        )
        logger.info("Uploaded %d nomenclatures to promotion %d", len(nomenclatures), promo_id)
        return data if isinstance(data, dict) else {}
