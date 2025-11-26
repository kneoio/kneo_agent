import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from api.queue_api_client import QueueAPIClient
from cnst.paths import MERGED_AUDIO_DIR

logger = logging.getLogger(__name__)

TEST_CHAT_ID = 123


async def _bg_queue_and_notify(
        brand: str,
        song_uuid: str,
        intro_text: str,
        priority: int,
        chat_id: int,
        operation_id: str
):
    from llm.llm_request import invoke_chat
    from rest.app_setup import cfg, llm_factory, TELEGRAM_TOKEN, get_audio_processor
    from cnst.llm_types import LlmType
    from util.template_loader import render_template

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

    except Exception as e:
        logger.error(f"Queue job failed: {e}", exc_info=True)
        if "ReadTimeout" in str(e) or "timeout" in str(e).lower():
            result_text = "Queue request timed out. The song may still be processing. Please wait a moment before trying again."
        else:
            result_text = f"Queue failed: {str(e)}"

    try:
        system_prompt = render_template("chat/queue_results_system.hbs", {})
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({
            "role": "user",
            "content": f"The queue operation completed: {result_text}"
        })

        llm_client = llm_factory.get_llm_client(
            LlmType.GROQ,
            enable_sound_fragment_tool=False,
            enable_listener_tool=False,
            enable_stations_tools=False
        )
        llm_result = await invoke_chat(llm_client=llm_client, messages=messages, return_full_history=False)
        reply = llm_result.actual_result

        if chat_id == TEST_CHAT_ID:
            print(f"[TEST MODE] Would send to Telegram chat_id={chat_id}: {reply}")
        else:
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": reply}
                )
    except Exception as e:
        logger.error(f"Error in _bg_queue_and_notify LLM trigger: {e}")


async def queue_intro_and_song(
        brand: str,
        song_uuid: str,
        intro_text: str,
        priority: int = 8,
        telegram_chat_id: Optional[int] = None
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
            telegram_chat_id,
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
            "name": "queue_intro_and_song",
            "description": "Queue a song with a custom intro message to the radio station. The intro_text will be converted to speech and played before the song. Use this when a listener requests a song or wants to send a message to the audience.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Brand slug (e.g., 'lumisonic')"},
                    "song_uuid": {"type": "string", "description": "UUID of the song to play (extract from SONG_MAP in conversation history)"},
                    "intro_text": {"type": "string", "description": "Text for the intro announcement (e.g., 'Now Rina requested by Mark' or 'Mark sends love to Filane with this song'). Keep it short and natural."},
                    "priority": {"type": "integer", "description": "Queue priority: 8=high, 9=medium, 10=normal", "minimum": 8, "maximum": 10, "default": 8},
                    "telegram_chat_id": {"type": "integer", "description": "Telegram chat ID of the requester"}
                },
                "required": ["brand", "song_uuid", "intro_text", "telegram_chat_id"]
            }
        }
    }
