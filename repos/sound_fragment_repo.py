from typing import List, Dict, Any
from uuid import UUID

from util.db_manager import DBManager


async def get_brand_songs(brand_id: UUID, fragment_type: str = "SONG") -> List[Dict[str, Any]]:
    await DBManager.init()
    pool = DBManager.get_pool()
    sql = (
        "SELECT t.id, t.title, t.artist, "
        "array_agg(lbl.loc_name->>'en') AS labels_en "
        "FROM kneobroadcaster__sound_fragments t "
        "JOIN kneobroadcaster__brand_sound_fragments bsf ON t.id = bsf.sound_fragment_id "
        "LEFT JOIN kneobroadcaster__sound_fragment_labels l ON l.id = t.id "
        "LEFT JOIN __labels lbl ON lbl.id = l.label_id "
        "WHERE bsf.brand_id = $1 AND t.archived = 0 AND t.type = UPPER($2) "
        "GROUP BY t.id, t.title, t.artist "
        "ORDER BY t.reg_date DESC"
    )
    async with pool.acquire() as conn:
        print(f"SQL: {sql}")
        print(f"PARAMS: ({brand_id}, {fragment_type})")
        rows = await conn.fetch(sql, brand_id, fragment_type)
    print(f"rows_count={len(rows)}")
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(dict(r))
    return out
