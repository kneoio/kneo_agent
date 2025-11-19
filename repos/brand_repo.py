from typing import Optional
from uuid import UUID

from util.db_manager import DBManager


async def resolve_brand_id(brand: str) -> Optional[UUID]:
    try:
        return UUID(brand)
    except Exception:
        pass

    term = (brand or "").strip()
    if not term:
        return None

    await DBManager.init()
    pool = DBManager.get_pool()
    async with pool.acquire() as conn:
        # exact by slug_name
        row = await conn.fetchrow(
            "SELECT id FROM kneobroadcaster__brands WHERE lower(slug_name) = lower($1) LIMIT 1",
            term,
        )
        if row and row.get("id"):
            print(f"resolve_brand_id: matched slug_name exactly -> {row.get('id')}")
            return row.get("id")

        like = f"%{term}%"
        # ilike contains slug_name
        row = await conn.fetchrow(
            "SELECT id FROM kneobroadcaster__brands WHERE slug_name ILIKE $1 LIMIT 1",
            like,
        )
        if row and row.get("id"):
            print(f"resolve_brand_id: matched slug_name ILIKE -> {row.get('id')}")
            return row.get("id")

        # loc_name values contains
        row = await conn.fetchrow(
            """
            SELECT id FROM kneobroadcaster__brands
            WHERE EXISTS (
                SELECT 1 FROM jsonb_each_text(loc_name) j
                WHERE j.value ILIKE $1
            )
            LIMIT 1
            """,
            like,
        )
        if row and row.get("id"):
            print(f"resolve_brand_id: matched loc_name ILIKE -> {row.get('id')}")
            return row.get("id")

        print("resolve_brand_id: no match")
        return None
