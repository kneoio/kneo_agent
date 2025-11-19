import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from elevenlabs.client import ElevenLabs

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from cnst.paths import MERGED_AUDIO_DIR
from mcp.queue_mcp import QueueMCP
from mcp.mcp_client import MCPClient
from models.live_container import LiveRadioStation
from repos.brand_repo import get_brand_preferred_voice_id
from tools.audio_processor import AudioProcessor

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


async def queue_intro_song(brand: str, song_uuid: str, intro_text: str, priority: int = 8) -> Dict[str, Any]:
    from rest.app_setup import cfg, mcp_client as app_mcp_client
    
    if not brand or not song_uuid or not intro_text:
        return {"success": False, "error": "brand, song_uuid and intro_text are required"}

    voice_id = await get_brand_preferred_voice_id(brand)
    if not voice_id:
        return {"success": False, "error": "preferred voice not configured for brand"}

    el_cfg = (cfg or {}).get("elevenlabs", {})
    el_key = el_cfg.get("api_key")
    if not el_key:
        return {"success": False, "error": "ElevenLabs api key missing in config"}

    api_client = BroadcasterAPIClient(cfg)
    interaction_memory = InteractionMemory(api_client=api_client, brand=brand)

    station = LiveRadioStation.from_dict({
        "name": brand,
        "slugName": brand,
        "radioStationStatus": "ACTIVE",
        "djName": "AI",
        "info": "",
        "tts": {"preferredVoice": voice_id, "secondaryVoice": "", "secondaryVoiceName": ""},
        "prompts": []
    })

    eleven = ElevenLabs(api_key=el_key)
    audio_processor = AudioProcessor(elevenlabs_inst=eleven, station=station, memory=interaction_memory)
    audio_data, reason = await audio_processor.generate_tts_audio(intro_text)
    if not audio_data:
        return {"success": False, "error": reason or "tts failed"}

    file_path = _save_audio_file(audio_data, brand)

    mcp: Optional[MCPClient] = app_mcp_client
    if not mcp:
        return {"success": False, "error": "MCP client not initialized"}

    queue = QueueMCP(mcp)
    try:
        result = await queue.add_to_queue_i_s(brand_name=brand, sound_fragment_uuid=song_uuid, file_path=file_path, priority=priority)
        ok = bool(result is True or (isinstance(result, dict) and result.get("success")))
        return {"success": ok, "result": result, "file_path": file_path}
    except Exception as e:
        logger.error(f"Queue add failed: {e}")
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
