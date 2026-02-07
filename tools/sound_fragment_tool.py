import asyncio
import uuid
from typing import Dict, Any, Optional

from api.sound_fragment_api import BrandSoundFragmentsAPI
from core.config import load_config

import logging
logger = logging.getLogger(__name__)

async def _bg_fetch_and_push(
        brand: str,
        keyword: Optional[str],
        limit: Optional[int],
        offset: Optional[int],
        operation_id: str
):
    config = load_config("config.yaml")

    try:
        api = BrandSoundFragmentsAPI(config)
        result = await api.search(
            brand,
            keyword=keyword,
            limit=limit,
            offset=offset
        )

        items_raw = result if isinstance(result, list) else result.get("items", [])
        lines = []
        song_map = {}
        for idx, r in enumerate(items_raw, start=1):
            title = r["title"]
            artist = r["artist"]
            song_id = r["id"]
            lines.append(f"#{idx}. {title} | {artist}")
            song_map[idx] = {"id": song_id, "title": title, "artist": artist}

        results_text = "\n".join(lines) if lines else "No results."
        results_text += f"\n\n[SONG_MAP:{song_map}]"
        
        search_type = "search" if keyword else "browse"
        logger.info(f"{search_type.capitalize()} results for '{keyword or 'latest'}': {len(items_raw)} items found")
        logger.info(f"Search results for {brand}: {results_text}")

    except Exception as e:
        logger.error(f"Search API error: {e}", exc_info=True)


async def get_brand_sound_fragment(
        brand: str,
        keyword: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> Dict[str, Any]:
    op_id = uuid.uuid4().hex

    asyncio.create_task(
        _bg_fetch_and_push(
            brand,
            keyword,
            limit,
            offset,
            op_id
        )
    )

    return {
        "success": True,
        "accepted": True,
        "processing": True,
        "operation_id": op_id
    }


