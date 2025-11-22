import math
import asyncio
import uuid
from dataclasses import asdict
from typing import Dict, Any, Optional
from uuid import UUID
import httpx

from models.page_view import BrandSongsResult, SongItem
from repos.brand_repo import resolve_brand_id
from repos.sound_fragment_repo import get_brand_songs


async def _bg_fetch_and_push(brand: str, fragment_type: str, page: int, page_size: int, chat_id: int, operation_id: Optional[str]):
    from rest.app_setup import TELEGRAM_TOKEN
    brand_uuid = None
    try:
        brand_uuid = UUID(brand)
    except Exception:
        brand_uuid = await resolve_brand_id(brand)
    if not brand_uuid:
        text = "No results for this brand."
    else:
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
        header = f"Showing page {page}/{total_pages} (total {total_count})"
        lines = []
        for idx, it in enumerate(items, start=1):
            t = it.title or ""
            a = it.artist or ""
            lines.append(f"#{idx}. {t} — {a}")
        if total_pages and page < total_pages:
            lines.append(f"Say 'next' or 'page {page+1}' for more.")
        body = "\n".join(lines)
        text = f"{header}\n{body}" if body else header
        if operation_id:
            text = f"op:{operation_id}\n" + text
    async with httpx.AsyncClient() as http_client:
        await http_client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )


async def get_brand_sound_fragment(brand: str, fragment_type: str = "SONG", page: int = 1, page_size: int = 20, notify_telegram_chat_id: Optional[int] = None, operation_id: Optional[str] = None) -> Dict[str, Any]:
    if notify_telegram_chat_id is not None:
        op_id = operation_id or uuid.uuid4().hex
        try:
            asyncio.create_task(_bg_fetch_and_push(brand, fragment_type, page, page_size, notify_telegram_chat_id, op_id))
            return {"success": True, "accepted": True, "processing": True, "operation_id": op_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    brand_uuid = None
    try:
        brand_uuid = UUID(brand)
    except Exception:
        brand_uuid = await resolve_brand_id(brand)
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
                    },
                    "notify_telegram_chat_id": {
                        "type": "integer"
                    },
                    "operation_id": {
                        "type": "string"
                    }
                },
                "required": ["brand"]
            }
        }
    }
