"""Mock WB API client for development without a real API key."""

import random
from typing import Any

from app.services.wb_api.client import BaseWBClient

MOCK_BRANDS = ["BrandAlpha", "BrandBeta", "BrandGamma"]
MOCK_CATEGORIES = ["Одежда", "Обувь", "Аксессуары", "Электроника", "Дом"]


class MockWBClient(BaseWBClient):
    """Returns realistic mock data for development."""

    async def get_products(self) -> list[dict[str, Any]]:
        products = []
        for i in range(1, 51):  # 50 mock products
            products.append({
                "nmID": 100000 + i,
                "vendorCode": f"ART-{i:04d}",
                "brand": random.choice(MOCK_BRANDS),
                "subjectName": random.choice(MOCK_CATEGORIES),
                "title": f"Товар {i} — тестовый артикул",
                "photos": [{"big": f"https://placeholder.co/400?text=Product{i}"}],
            })
        return products

    async def get_prices(self) -> list[dict[str, Any]]:
        return [
            {
                "nmId": 100000 + i,
                "price": random.randint(500, 5000),
                "discount": random.randint(5, 30),
            }
            for i in range(1, 51)
        ]

    async def set_prices(self, prices: list[dict[str, Any]]) -> dict[str, Any]:
        return {"status": "ok", "updated": len(prices)}

    async def get_stocks(self) -> list[dict[str, Any]]:
        return [
            {
                "nmId": 100000 + i,
                "warehouseId": random.choice([507, 117986, 120762]),
                "warehouseName": random.choice(["Коледино", "Подольск", "Казань"]),
                "quantity": random.randint(0, 500),
            }
            for i in range(1, 51)
        ]

    async def get_orders(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        return [
            {
                "nmId": 100000 + random.randint(1, 50),
                "date": date_from,
                "totalPrice": random.randint(500, 5000),
                "spp": random.randint(5, 25),
                "isCancel": random.random() < 0.1,
            }
            for _ in range(random.randint(20, 100))
        ]

    async def get_sales(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        return [
            {
                "nmId": 100000 + random.randint(1, 50),
                "date": date_from,
                "totalPrice": random.randint(500, 5000),
                "forPay": random.randint(300, 4000),
                "isReturn": random.random() < 0.05,
            }
            for _ in range(random.randint(15, 80))
        ]

    async def get_promotions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "promo_001",
                "name": "Весенняя распродажа",
                "startDate": "2026-03-01",
                "endDate": "2026-03-15",
                "discount": 15,
            },
            {
                "id": "promo_002",
                "name": "День рождения WB",
                "startDate": "2026-04-01",
                "endDate": "2026-04-07",
                "discount": 20,
            },
        ]

    async def get_commissions(self) -> list[dict[str, Any]]:
        return [
            {"subjectName": cat, "commission": random.randint(5, 20)}
            for cat in MOCK_CATEGORIES
        ]
