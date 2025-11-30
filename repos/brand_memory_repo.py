from datetime import date, datetime
from typing import Any, Dict, Optional
import json

from util.db_manager import DBManager
from models.brand_memory import BrandMemory


class BrandMemoryRepo:
    async def get(self, brand: str, day: date) -> Optional[BrandMemory]:
        await DBManager.init()
        pool = DBManager.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, last_mod_date, brand, day, summary FROM mixpla__brand_memory WHERE brand = $1 AND day = $2 LIMIT 1",
                brand,
                day,
            )
            if not row:
                return None
            summary_raw = row.get("summary")
            summary_dict = json.loads(summary_raw) if isinstance(summary_raw, str) else summary_raw
            return BrandMemory(
                id=row.get("id"),
                last_mod_date=row.get("last_mod_date"),
                brand=row.get("brand"),
                day=row.get("day"),
                summary=summary_dict,
            )

    async def insert(self, brand: str, day: date, summary: Dict[str, Any]) -> BrandMemory:
        await DBManager.init()
        pool = DBManager.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mixpla__brand_memory (last_mod_date, brand, day, summary)
                VALUES (now(), $1, $2, $3::jsonb)
                RETURNING id, last_mod_date, brand, day, summary
                """,
                brand,
                day,
                json.dumps(summary),
            )
            summary_raw = row.get("summary")
            summary_dict = json.loads(summary_raw) if isinstance(summary_raw, str) else summary_raw
            return BrandMemory(
                id=row.get("id"),
                last_mod_date=row.get("last_mod_date"),
                brand=row.get("brand"),
                day=row.get("day"),
                summary=summary_dict,
            )

    async def update(self, brand: str, day: date, summary: Dict[str, Any]) -> BrandMemory:
        await DBManager.init()
        pool = DBManager.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE mixpla__brand_memory 
                SET last_mod_date = now(), summary = $3::jsonb
                WHERE brand = $1 AND day = $2
                RETURNING id, last_mod_date, brand, day, summary
                """,
                brand,
                day,
                json.dumps(summary),
            )
            if not row:
                raise ValueError(f"No existing record found for brand {brand} on {day}")
            summary_raw = row.get("summary")
            summary_dict = json.loads(summary_raw) if isinstance(summary_raw, str) else summary_raw
            return BrandMemory(
                id=row.get("id"),
                last_mod_date=row.get("last_mod_date"),
                brand=row.get("brand"),
                day=row.get("day"),
                summary=summary_dict,
            )


brand_memory_repo = BrandMemoryRepo()


async def get_brand_memory(brand: str, day: date) -> Optional[BrandMemory]:
    return await brand_memory_repo.get(brand, day)


async def insert_brand_memory(brand: str, day: date, summary: Dict[str, Any]) -> BrandMemory:
    return await brand_memory_repo.insert(brand, day, summary)
