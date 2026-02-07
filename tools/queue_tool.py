import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from api.queue_api_client import QueueAPIClient
from cnst.paths import MERGED_AUDIO_DIR

logger = logging.getLogger(__name__)

async def _bg_queue_and_notify(
        brand: str,
        song_uuid: str,
        intro_text: str,
        priority: int,
        operation_id: str
):
    from rest.app_setup import get_audio_processor

    result_text = ""
    try:
        from rest.app_setup import cfg
        audio_processor = get_audio_processor()
        elevenlabs_cfg = cfg.get("elevenlabs", {})
        voice_id = elevenlabs_cfg.get("default_voice_id")
        
        logger.info(f"Generating TTS for intro: {intro_text[:50]}...")
        audio_data, reason = await audio_processor.generate_tts_simple(intro_text, voice_id)
        
        if not audio_data:
            raise ValueError(f"TTS generation failed: {reason}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{brand}_mixplaclone_intro_{timestamp}_{operation_id[:8]}.mp3"
        tts_path = str(MERGED_AUDIO_DIR / filename)
        
        with open(tts_path, "wb") as f:
            f.write(audio_data)
        
        logger.info(f"TTS saved to {tts_path}")
        
        client = QueueAPIClient(cfg)
        process_id = uuid.uuid4().hex

        payload = {
            "mergingMethod": "INTRO_SONG",
            "soundFragments": {"song1": song_uuid},
            "filePaths": {"audio1": tts_path},
            "priority": priority
        }

        enqueue_result = await client.enqueue_add(
            brand=brand,
            process_id=process_id,
            payload=payload
        )

        logger.info(f"Queue enqueue successful for {brand}, process_id={process_id}")
        result_text = f"Successfully queued intro+song for {brand}. The song will play shortly."
        logger.info(f"Queue operation result: {result_text}")

    except Exception as e:
        logger.error(f"Queue job failed: {e}", exc_info=True)
        if "ReadTimeout" in str(e) or "timeout" in str(e).lower():
            logger.error("Queue request timed out. The song may still be processing.")
        else:
            logger.error(f"Queue failed: {str(e)}")


async def queue_intro_and_song(
        brand: str,
        song_uuid: str,
        intro_text: str,
        priority: int = 8
) -> Dict[str, Any]:

    if not brand or not song_uuid or not intro_text:
        return {"success": False, "error": "brand, song_uuid, intro_text are required"}

    op_id = uuid.uuid4().hex

    asyncio.create_task(
        _bg_queue_and_notify(
            brand,
            song_uuid,
            intro_text,
            priority,
            op_id
        )
    )

    return {
        "success": True,
        "accepted": True,
        "processing": True,
        "operation_id": op_id
    }


