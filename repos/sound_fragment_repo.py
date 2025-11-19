from typing import List, Dict, Any
from uuid import UUID

from util.db_manager import DBManager


async def get_brand_songs(brand_id: UUID, fragment_type: str = "SONG", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    await DBManager.init()
    pool = DBManager.get_pool()
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    offset = (page - 1) * page_size
    count_sql = (
        "SELECT COUNT(DISTINCT t.id) AS cnt "
        "FROM kneobroadcaster__sound_fragments t "
        "JOIN kneobroadcaster__brand_sound_fragments bsf ON t.id = bsf.sound_fragment_id "
        "LEFT JOIN kneobroadcaster__sound_fragment_labels l ON l.id = t.id "
        "LEFT JOIN __labels lbl ON lbl.id = l.label_id "
        "WHERE bsf.brand_id = $1 AND t.archived = 0 AND t.type = UPPER($2)"
    )
    data_sql = (
        "SELECT t.id, t.title, t.artist, "
        "array_agg(lbl.loc_name->>'en') AS labels_en "
        "FROM kneobroadcaster__sound_fragments t "
        "JOIN kneobroadcaster__brand_sound_fragments bsf ON t.id = bsf.sound_fragment_id "
        "LEFT JOIN kneobroadcaster__sound_fragment_labels l ON l.id = t.id "
        "LEFT JOIN __labels lbl ON lbl.id = l.label_id "
        "WHERE bsf.brand_id = $1 AND t.archived = 0 AND t.type = UPPER($2) "
        "GROUP BY t.id, t.title, t.artist "
        "ORDER BY t.reg_date DESC "
        "LIMIT $3 OFFSET $4"
    )
    async with pool.acquire() as conn:
        print(f"SQL_COUNT: {count_sql}")
        print(f"PARAMS_COUNT: ({brand_id}, {fragment_type})")
        cnt_row = await conn.fetchrow(count_sql, brand_id, fragment_type)
        total_count = int(cnt_row[0]) if cnt_row is not None else 0
        print(f"SQL_DATA: {data_sql}")
        print(f"PARAMS_DATA: ({brand_id}, {fragment_type}, {page_size}, {offset})")
        rows = await conn.fetch(data_sql, brand_id, fragment_type, page_size, offset)
    print(f"rows_count_page={len(rows)} total_count={total_count}")
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append(dict(r))
    return {"items": items, "total_count": total_count}
