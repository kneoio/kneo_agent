import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID

from util.db_manager import DBManager


async def get_brand_songs_with_labels(brand_id: UUID, fragment_type: str = "SONG", limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    await DBManager.init()
    pool = DBManager.get_pool()
    sql = (
        "SELECT t.*, "
        "COALESCE(array_agg(DISTINCT l.label_id) FILTER (WHERE l.label_id IS NOT NULL), '{}') AS labels "
        "FROM kneobroadcaster__sound_fragments t "
        "JOIN kneobroadcaster__brand_sound_fragments bsf ON t.id = bsf.sound_fragment_id "
        "LEFT JOIN kneobroadcaster__sound_fragment_labels l ON l.id = t.id "
        "WHERE bsf.brand_id = $1 AND t.archived = 0 AND t.type = $2 "
        "GROUP BY t.id "
        "ORDER BY bsf.played_by_brand_count ASC, COALESCE(bsf.last_time_played_by_brand, '1970-01-01'::timestamp) ASC "
        "LIMIT $3 OFFSET $4"
    )
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, brand_id, fragment_type, limit, offset)
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            out.append(d)
        return out
