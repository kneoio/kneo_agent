from typing import Optional
from uuid import UUID
import json

from util.db_manager import DBManager


class BrandRepo:
    async def resolve_brand_id(self, brand: str) -> Optional[UUID]:
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
            row = await conn.fetchrow(
                "SELECT id FROM kneobroadcaster__brands WHERE lower(slug_name) = lower($1) LIMIT 1",
                term,
            )
            if row and row.get("id"):
                print(f"resolve_brand_id: matched slug_name exactly -> {row.get('id')}")
                return row.get("id")
            like = f"%{term}%"
            row = await conn.fetchrow(
                "SELECT id FROM kneobroadcaster__brands WHERE slug_name ILIKE $1 LIMIT 1",
                like,
            )
            if row and row.get("id"):
                print(f"resolve_brand_id: matched slug_name ILIKE -> {row.get('id')}")
                return row.get("id")
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

    async def get_brand_preferred_voice_id(self, brand: str) -> Optional[str]:
        bid = await self.resolve_brand_id(brand)
        if not bid:
            return None
        await DBManager.init()
        pool = DBManager.get_pool()
        async with pool.acquire() as conn:
            sql_voice = (
                "SELECT a.preferred_voice "
                "FROM kneobroadcaster__brands b "
                "JOIN kneobroadcaster__ai_agents a ON b.ai_agent_id = a.id "
                "WHERE b.id = $1 "
                "LIMIT 1"
            )
            print(f"SQL: {sql_voice}")
            print(f"PARAMS: ({bid},)")
            row = await conn.fetchrow(sql_voice, bid)
            if not row:
                print("no rows returned")
                return None
            pref = row.get("preferred_voice")
            print(f"preferred_voice_raw={pref} type={type(pref).__name__}")
            if isinstance(pref, str):
                try:
                    pref = json.loads(pref)
                except Exception:
                    pref = None
            if isinstance(pref, dict):
                vid = pref.get("id")
                print(f"voice_id={vid}")
                return vid
            if isinstance(pref, list) and pref:
                item = pref[0]
                vid = item.get("id") if isinstance(item, dict) else None
                print(f"voice_id={vid}")
                return vid
            print("preferred_voice empty or invalid")
            return None


brand_repo = BrandRepo()


async def resolve_brand_id(brand: str) -> Optional[UUID]:
    return await brand_repo.resolve_brand_id(brand)


async def get_brand_preferred_voice_id(brand: str) -> Optional[str]:
    return await brand_repo.get_brand_preferred_voice_id(brand)
