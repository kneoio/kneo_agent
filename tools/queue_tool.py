import logging
import uuid
from typing import Optional, Dict, Any
from rest.app_setup import cfg, TELEGRAM_TOKEN
import httpx

from api.queue_api_client import QueueAPIClient

logger = logging.getLogger(__name__)


async def enqueue_intro_song_rest(
        brand: str,
        intro_uuid: str,
        song_uuid: str,
        overlay_path: str,
        priority: int = 100,
        notify_telegram_chat_id: Optional[int] = None
) -> Dict[str, Any]:
    from rest.app_setup import cfg, TELEGRAM_TOKEN

    logger.info(
        f"enqueue_intro_song_rest accepted: brand={brand}, intro_uuid={intro_uuid}, "
        f"song_uuid={song_uuid}, overlay_path={overlay_path}, priority={priority}"
    )

    if not brand or not intro_uuid or not song_uuid or not overlay_path:
        return {"success": False, "error": "brand, intro_uuid, song_uuid, overlay_path are required"}

    try:
        client = QueueAPIClient(cfg)
        process_id = uuid.uuid4().hex

        payload = {
            "mergingMethod": "INTRO_SONG",
            "soundFragments": {"1": intro_uuid, "2": song_uuid},
            "filePaths": {"1": overlay_path},
            "priority": priority
        }

        enqueue_result = await client.enqueue_add(
            brand=brand,
            process_id=process_id,
            payload=payload
        )

        last_event = await client.wait_until_done(brand, process_id)

        if notify_telegram_chat_id is not None:
            text = f"Queue job completed for {brand}. processId={process_id}"
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": notify_telegram_chat_id, "text": text}
                )

        return {
            "success": True,
            "process_id": process_id,
            "enqueue_result": enqueue_result,
            "last_event": last_event
        }
    except Exception as e:
        logger.error(f"enqueue_intro_song_rest failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def enqueue_merge_rest(
        brand: str,
        merging_method: str,
        sound_fragments: Dict[str, str],
        file_paths: Dict[str, str],
        priority: int = 100,
        notify_telegram_chat_id: Optional[int] = None,
) -> Dict[str, Any]:
    if not brand or not merging_method or not sound_fragments or not file_paths:
        return {"success": False, "error": "brand, merging_method, sound_fragments, file_paths are required"}

    try:
        client = QueueAPIClient(cfg)
        process_id = uuid.uuid4().hex

        payload: Dict[str, Any] = {
            "mergingMethod": merging_method,
            "soundFragments": sound_fragments,
            "filePaths": file_paths,
            "priority": priority,
        }

        enqueue_result = await client.enqueue_add(
            brand=brand,
            process_id=process_id,
            payload=payload
        )

        last_event = await client.wait_until_done(brand, process_id)

        if notify_telegram_chat_id is not None:
            text = f"Queue job completed for {brand}. processId={process_id}"
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": notify_telegram_chat_id, "text": text}
                )

        return {
            "success": True,
            "process_id": process_id,
            "enqueue_result": enqueue_result,
            "last_event": last_event
        }
    except Exception as e:
        logger.error(f"enqueue_merge_rest failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def get_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "queue_intro_song",
            "description": "Generate a short intro via TTS and enqueue INTRO+SONG to the brand's radio queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Brand slug or UUID"},
                    "song_uuid": {"type": "string", "description": "UUID of the selected song"},
                    "intro_text": {"type": "string", "description": "Short on-air intro text"},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8}
                },
                "required": ["brand", "song_uuid", "intro_text"]
            }
        }
    }
