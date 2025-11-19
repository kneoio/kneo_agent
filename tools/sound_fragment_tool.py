from typing import List, Dict, Any
from uuid import UUID
import math

from repos.brand_repo import resolve_brand_id
from repos.sound_fragment_repo import get_brand_songs
from models.page_view import BrandSongsResult, SongItem
from dataclasses import asdict


async def get_brand_sound_fragment(brand: str, fragment_type: str = "SONG", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    brand_uuid = None
    try:
        brand_uuid = UUID(brand)
    except Exception:
        brand_uuid = await resolve_brand_id(brand)
    print(f"get_brand_sound_fragment: brand_input={brand}, resolved_uuid={brand_uuid}, fragment_type={fragment_type}", flush=True)
    if not brand_uuid:
        container = BrandSongsResult(brand=brand, fragment_type=fragment_type, total_count=0, songs=[], page=page, page_size=page_size, total_pages=0)
        return asdict(container)
    result = await get_brand_songs(brand_uuid, fragment_type, page=page, page_size=page_size)
    items_raw = result.get("items") if isinstance(result, dict) else None
    total_count = int(result.get("total_count", 0)) if isinstance(result, dict) else 0
    items: list[SongItem] = []
    if items_raw:
        for r in items_raw:
            sid = r.get("id")
            title = r.get("title")
            artist = r.get("artist")
            labels_en = r.get("labels_en")
            items.append(SongItem(id=str(sid) if sid is not None else None, title=title, artist=artist, labels_en=labels_en))
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    container = BrandSongsResult(brand=brand, fragment_type=fragment_type, total_count=total_count, songs=items, page=page, page_size=page_size, total_pages=total_pages)
    return asdict(container)


def get_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "get_brand_sound_fragment",
            "description": "Retrieve sound fragments for a specific brand and fragment type from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {
                        "type": "string",
                        "description": "Brand UUID as string"
                    },
                    "fragment_type": {
                        "type": "string",
                        "enum": ["SONG", "JINGLE", "ADVERTISEMENT"],
                        "description": "Type of fragment to retrieve"
                    },
                    "page": {
                        "type": "integer",
                        "minimum": 1,
                        "default": 1
                    },
                    "page_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20
                    }
                },
                "required": ["brand"]
            }
        }
    }
