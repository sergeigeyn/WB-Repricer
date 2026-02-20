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

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )
            response.raise_for_status()
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

    async def get_stocks(self, barcodes: list[str]) -> dict[str, int]:
        """Fetch stock quantities across all seller warehouses.

        Args:
            barcodes: List of product barcodes (SKUs) to query.

        Returns: {barcode: total_quantity}
        """
        warehouses = await self.get_warehouses()
        stock_map: dict[str, int] = {}

        # Split barcodes into chunks of 1000 (API limit)
        chunks = [barcodes[i:i + 1000] for i in range(0, len(barcodes), 1000)]

        for wh in warehouses:
            wh_id = wh.get("id")
            if not wh_id:
                continue
            for chunk in chunks:
                try:
                    data = await self._request(
                        "POST",
                        f"{WB_MARKETPLACE}/api/v3/stocks/{wh_id}",
                        json={"skus": chunk},
                    )
                    for item in data.get("stocks", []):
                        sku = item.get("sku", "")
                        qty = item.get("amount", 0)
                        if sku:
                            stock_map[sku] = stock_map.get(sku, 0) + qty
                except Exception as e:
                    logger.warning("Stocks for warehouse %s failed: %s", wh_id, e)

        logger.info("Fetched stocks from %d warehouses, %d SKUs", len(warehouses), len(stock_map))
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
