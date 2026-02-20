"""WB API client abstraction layer.

WB uses different domains per API section:
- content-api.wildberries.ru — product cards
- discounts-prices-api.wildberries.ru — prices & discounts
- statistics-api.wildberries.ru — orders & sales history
- marketplace-api.wildberries.ru — FBO/FBS orders, stocks, warehouses
- advert-api.wildberries.ru — advertising campaigns
"""

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

    async def get_paid_storage(self, date_from: str) -> list[dict[str, Any]]:
        """Fetch paid storage data per product per warehouse per day.

        Returns list of storage entries with nmId, warehousePrice, storagePricePerBarcode, etc.
        Uses Seller Analytics API /api/v1/paid_storage.
        """
        data = await self._request_with_timeout(
            60.0,
            "GET",
            f"{WB_ANALYTICS}/api/v1/paid_storage",
            params={"dateFrom": date_from},
        )
        items = data if isinstance(data, list) else []
        logger.info("Fetched %d paid storage entries from WB", len(items))
        return items

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
