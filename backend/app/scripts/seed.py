"""
Seed-script: opret standard danske webshops i databasen.
Kør med: python -m app.scripts.seed
"""
from __future__ import annotations

import asyncio
import uuid

from app.database import AsyncSessionLocal
from app.models.shop import Shop
from sqlalchemy import select

SHOPS = [
    {
        "id": uuid.uuid4(),
        "name": "Compumail",
        "domain": "compumail.dk",
        "logo_url": "https://www.compumail.dk/media/logo/stores/1/logo.png",
        "default_provider": "http",
    },
    {
        "id": uuid.uuid4(),
        "name": "Computersalg",
        "domain": "computersalg.dk",
        "logo_url": None,
        "default_provider": "http",
    },
    {
        "id": uuid.uuid4(),
        "name": "Elsalg",
        "domain": "elsalg.dk",
        "logo_url": None,
        "default_provider": "http",
    },
    {
        "id": uuid.uuid4(),
        "name": "Happii",
        "domain": "happii.dk",
        "logo_url": None,
        "default_provider": "http",
    },
    {
        "id": uuid.uuid4(),
        "name": "Komplett",
        "domain": "komplett.dk",
        "logo_url": None,
        "default_provider": "http",
    },
    {
        "id": uuid.uuid4(),
        "name": "Proshop",
        "domain": "proshop.dk",
        "logo_url": None,
        "default_provider": "playwright",
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for shop_data in SHOPS:
            existing = (
                await db.execute(select(Shop).where(Shop.domain == shop_data["domain"]))
            ).scalar_one_or_none()

            if existing:
                print(f"  skip  {shop_data['domain']} (eksisterer allerede)")
                continue

            shop = Shop(**shop_data)
            db.add(shop)
            print(f"  create {shop_data['domain']}")

        await db.commit()
    print("Seed færdig.")


if __name__ == "__main__":
    asyncio.run(seed())
