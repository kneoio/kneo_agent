from typing import List, Dict, Any
from uuid import UUID

from repos.brand_repo import resolve_brand_id
from repos.sound_fragment_repo import get_brand_songs


async def get_brand_sound_fragment(brand: str, fragment_type: str = "SONG") -> Dict[str, Any]:
    brand_uuid = None
    try:
        brand_uuid = UUID(brand)
    except Exception:
        brand_uuid = await resolve_brand_id(brand)
    print(f"get_brand_sound_fragment: brand_input={brand}, resolved_uuid={brand_uuid}, fragment_type={fragment_type}", flush=True)
    if not brand_uuid:
        return {"brand": brand, "fragment_type": fragment_type, "songs": []}
    songs = await get_brand_songs(brand_uuid, fragment_type)
    total_count = len(songs) if songs else 0
    items = []
    if songs:
        for r in songs[:20]:
            sid = r.get("id")
            title = r.get("title")
            artist = r.get("artist")
            labels_en = r.get("labels_en")
            items.append({"id": str(sid) if sid is not None else None, "title": title, "artist": artist, "labels_en": labels_en})
    return {"brand": brand, "fragment_type": fragment_type, "total_count": total_count, "songs": items}


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
                    }
                },
                "required": ["brand"]
            }
        }
    }
