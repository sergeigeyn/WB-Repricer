"""Quick test: check WB Calendar API response."""
import asyncio
import os

import httpx
from app.core.database import async_session
from app.core.security import decrypt_api_key
from app.models.product import WBAccount
from sqlalchemy import select


async def main():
    async with async_session() as db:
        result = await db.execute(select(WBAccount).limit(1))
        account = result.scalar_one_or_none()
        if not account:
            print("No WB account found")
            return

        key = decrypt_api_key(account.api_key_encrypted)
        print(f"API key: {key[:20]}...")
        headers = {"Authorization": key}

        async with httpx.AsyncClient(timeout=30) as client:
            # Test 1: GET /api/v1/calendar/promotions (basic)
            print("\n--- Test 1: GET /api/v1/calendar/promotions ---")
            r = await client.get(
                "https://dp-calendar-api.wildberries.ru/api/v1/calendar/promotions",
                headers=headers,
            )
            print(f"Status: {r.status_code}")
            print(f"Body: {r.text[:1000]}")

            # Test 2: Maybe POST instead of GET?
            print("\n--- Test 2: POST /api/v1/calendar/promotions ---")
            r2 = await client.post(
                "https://dp-calendar-api.wildberries.ru/api/v1/calendar/promotions",
                headers=headers,
            )
            print(f"Status: {r2.status_code}")
            print(f"Body: {r2.text[:1000]}")

            # Test 3: Try with allPromo param
            print("\n--- Test 3: GET with allPromo=true ---")
            r3 = await client.get(
                "https://dp-calendar-api.wildberries.ru/api/v1/calendar/promotions",
                headers=headers,
                params={"allPromo": "true"},
            )
            print(f"Status: {r3.status_code}")
            print(f"Body: {r3.text[:1000]}")


asyncio.run(main())
