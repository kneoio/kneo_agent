import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import time
import httpx

from api.queue_api_client import QueueAPIClient
from cnst.paths import MERGED_AUDIO_DIR

logger = logging.getLogger(__name__)


def _save_audio_file(audio_data: bytes, brand: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "wav" if (audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE") else "mp3"
    file_name = f"{brand}_intro_{ts}.{ext}"
    os.makedirs(str(MERGED_AUDIO_DIR), exist_ok=True)
    path = os.path.join(str(MERGED_AUDIO_DIR), file_name)
    with open(path, "wb") as f:
        f.write(audio_data)
    return path


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


async def enqueue_intro_song_rest(brand: str, intro_uuid: str, song_uuid: str, overlay_path: str, priority: int = 100, notify_telegram_chat_id: Optional[int] = None) -> Dict[str, Any]:
    from rest.app_setup import cfg, TELEGRAM_TOKEN
    logger.info(f"enqueue_intro_song_rest accepted: brand={brand}, intro_uuid={intro_uuid}, song_uuid={song_uuid}, overlay_path={overlay_path}, priority={priority}")
    if not brand or not intro_uuid or not song_uuid or not overlay_path:
        return {"success": False, "error": "brand, intro_uuid, song_uuid, overlay_path are required"}
    try:
        client = QueueAPIClient(cfg)
        upload_id = uuid.uuid4().hex
        start_ms = int(time.time() * 1000)
        payload = {
            "mergingMethod": "INTRO_SONG",
            "soundFragments": {"1": intro_uuid, "2": song_uuid},
            "filePaths": {"1": overlay_path},
            "priority": priority
        }
        enqueue_result = await client.enqueue_add(brand=brand, upload_id=upload_id, start_ms=start_ms, payload=payload)
        last_event = await client.wait_until_done(upload_id)
        if notify_telegram_chat_id is not None:
            text = f"Queue job completed for {brand}. uploadId={upload_id}"
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": notify_telegram_chat_id, "text": text}
                )
        return {"success": True, "upload_id": upload_id, "enqueue_result": enqueue_result, "last_event": last_event}
    except Exception as e:
        logger.error(f"enqueue_intro_song_rest failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def enqueue_merge_rest(
    brand: str,
    merging_method: str,
    sound_fragments: Dict[str, str],
    file_paths: Dict[str, str],
    priority: int = 100,
    start_ms: Optional[int] = None,
    upload_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    notify_telegram_chat_id: Optional[int] = None,
) -> Dict[str, Any]:
    from rest.app_setup import cfg, TELEGRAM_TOKEN
    if not brand or not merging_method or not sound_fragments or not file_paths:
        return {"success": False, "error": "brand, merging_method, sound_fragments, file_paths are required"}
    try:
        client = QueueAPIClient(cfg)
        up_id = upload_id or uuid.uuid4().hex
        st_ms = start_ms if start_ms is not None else int(time.time() * 1000)
        payload: Dict[str, Any] = {
            "mergingMethod": merging_method,
            "soundFragments": sound_fragments,
            "filePaths": file_paths,
            "priority": priority,
        }
        if operation_id:
            payload["operationId"] = operation_id
        enqueue_result = await client.enqueue_add(brand=brand, upload_id=up_id, start_ms=st_ms, payload=payload)
        last_event = await client.wait_until_done(up_id)
        if notify_telegram_chat_id is not None:
            text = f"Queue job completed for {brand}. uploadId={up_id}"
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": notify_telegram_chat_id, "text": text}
                )
        return {"success": True, "upload_id": up_id, "enqueue_result": enqueue_result, "last_event": last_event}
    except Exception as e:
        logger.error(f"enqueue_merge_rest failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
