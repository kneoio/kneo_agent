import logging
import uuid
from typing import Optional, Dict, Any
import httpx

from api.queue_api_client import QueueAPIClient

logger = logging.getLogger(__name__)


async def queue_intro_and_song(
        brand: str,
        song_uuid: str,
        generated_tts_path: str,
        priority: int = 8,
        notify_telegram_chat_id: Optional[int] = None
) -> Dict[str, Any]:

    if not brand or not song_uuid or not generated_tts_path:
        return {"success": False, "error": "brand, song_uuid, generated_tts_path are required"}

    try:
        from rest.app_setup import cfg, TELEGRAM_TOKEN
        client = QueueAPIClient(cfg)
        process_id = uuid.uuid4().hex

        payload = {
            "mergingMethod": "INTRO_SONG",
            "soundFragments": {"song1": song_uuid},
            "filePaths": {"audio1": generated_tts_path},
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


async def enqueue(
        brand: str,
        merging_method: str,
        sound_fragments: Dict[str, str],
        file_paths: Dict[str, str],
        priority: int = 10,
) -> Dict[str, Any]:
    if not brand or not merging_method or not sound_fragments or not file_paths:
        return {"success": False, "error": "brand, merging_method, sound_fragments, file_paths are required"}

    try:
        from rest.app_setup import cfg
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
                    "brand": {"type": "string", "description": "Brand slug"},
                    "song_uuid": {"type": "string", "description": "UUID of the selected song"},
                    "generated_tts_path": {"type": "string", "description": "Path to generated TTS file"},
                    "priority": {"type": "integer", "description": "Priority of the queue item", "minimum": 8, "maximum": 10, "default": 8}
                },
                "required": ["brand", "song_uuid", "generated_tts_path"]
            }
        }
    }
