import asyncio
import uuid
from typing import Dict, Any, Optional

import httpx

from api.sound_fragment_api import BrandSoundFragmentsAPI
from core.config import load_config


async def _bg_fetch_and_push(
        brand: str,
        keyword: str,
        limit: Optional[int],
        offset: Optional[int],
        chat_id: int,
        operation_id: str
):
    config = load_config("config.yaml")
    telegram_token = config.get("telegram", {}).get("token", "")
    
    try:
        api = BrandSoundFragmentsAPI(config)
        result = await api.search(
            brand,
            keyword=keyword,
            limit=limit,
            offset=offset
        )

        items_raw = result.get("items", [])
        lines = []
        for idx, r in enumerate(items_raw, start=1):
            title = r.get("title")
            artist = r.get("artist")
            id = r.get("id")
            lines.append(f"#{idx}. {title} | {artist}")

        text = "\n".join(lines) if lines else "No results."
        text = f"operation_id:{operation_id}\n{text}"
    except Exception as e:
        text = f"operation_id:{operation_id},Error: {str(e)}"

    async with httpx.AsyncClient() as http_client:
        await http_client.post(
            f"https://api.telegram.org/bot{telegram_token}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )


async def get_brand_sound_fragment(
        brand: str,
        keyword: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        notify_telegram_chat_id: Optional[int] = None
) -> Dict[str, Any]:
    op_id = uuid.uuid4().hex

    asyncio.create_task(
        _bg_fetch_and_push(
            brand,
            keyword,
            limit,
            offset,
            notify_telegram_chat_id,
            op_id
        )
    )
    
    return {
        "success": True,
        "accepted": True,
        "processing": True,
        "operation_id": op_id
    }


def get_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "get_brand_sound_fragment",
            "description": "Search brand sound fragments by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string"},
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                    "notify_telegram_chat_id": {"type": "integer"}
                },
                "required": ["brand", "keyword"]
            }
        }
    }
