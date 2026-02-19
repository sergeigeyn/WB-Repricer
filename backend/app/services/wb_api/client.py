"""WB API client abstraction layer.

If WB changes their API, only this file needs to be updated.
Supports mock mode for development without a real API key.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class BaseWBClient(ABC):
    """Abstract WB API client interface."""

    @abstractmethod
    async def get_products(self) -> list[dict[str, Any]]:
        """Get list of products from WB cabinet."""

    @abstractmethod
    async def get_prices(self) -> list[dict[str, Any]]:
        """Get current prices."""

    @abstractmethod
    async def set_prices(self, prices: list[dict[str, Any]]) -> dict[str, Any]:
        """Set prices for products."""

    @abstractmethod
    async def get_stocks(self) -> list[dict[str, Any]]:
        """Get warehouse stock levels."""

    @abstractmethod
    async def get_orders(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Get orders for date range."""

    @abstractmethod
    async def get_sales(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Get sales for date range."""

    @abstractmethod
    async def get_promotions(self) -> list[dict[str, Any]]:
        """Get available promotions."""

    @abstractmethod
    async def get_commissions(self) -> list[dict[str, Any]]:
        """Get WB commission rates."""


class WBApiClient(BaseWBClient):
    """Real WB API client using HTTP requests."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.WB_API_KEY
        self.base_url = settings.WB_API_BASE_URL
        self.headers = {"Authorization": self.api_key}
        self.timeout = 30.0

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method, f"{self.base_url}{url}", headers=self.headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_products(self) -> list[dict[str, Any]]:
        # WB Content API: /content/v2/get/cards/list
        data = await self._request(
            "POST",
            "/content/v2/get/cards/list",
            json={"settings": {"cursor": {"limit": 1000}, "filter": {"withPhoto": -1}}},
        )
        return data.get("cards", [])

    async def get_prices(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/public/api/v1/info")
        return data if isinstance(data, list) else []

    async def set_prices(self, prices: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._request("POST", "/public/api/v1/prices", json=prices)

    async def get_stocks(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/v3/stocks/0")
        return data.get("stocks", [])

    async def get_orders(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/v1/supplier/orders?dateFrom={date_from}&dateTo={date_to}"
        )
        return data if isinstance(data, list) else []

    async def get_sales(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/api/v1/supplier/sales?dateFrom={date_from}&dateTo={date_to}"
        )
        return data if isinstance(data, list) else []

    async def get_promotions(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/adv/v1/promotion/list")
        return data if isinstance(data, list) else []

    async def get_commissions(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/v1/supplier/commissions")
        return data if isinstance(data, list) else []


def get_wb_client() -> BaseWBClient:
    """Factory: return mock or real client based on config."""
    if settings.WB_API_MOCK_MODE:
        from app.services.wb_api.mock_client import MockWBClient
        return MockWBClient()
    return WBApiClient()
