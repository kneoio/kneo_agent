import asyncio
import logging
import uuid
from typing import Optional, Dict, Any
import httpx

from api.queue_api_client import QueueAPIClient

logger = logging.getLogger(__name__)

TEST_CHAT_ID = 123


async def _bg_queue_and_notify(
        brand: str,
        song_uuid: str,
        generated_tts_path: str,
        priority: int,
        chat_id: int,
        operation_id: str
):
    from util.db_manager import DBManager
    from memory.user_memory_manager import UserMemoryManager
    from repos.history_repo import HistoryRepository
    from llm.llm_request import invoke_chat
    from rest.app_setup import cfg, llm_factory, TELEGRAM_TOKEN
    from cnst.llm_types import LlmType
    from util.template_loader import render_template

    try:
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

        result_text = f"Queue request accepted for {brand}."

    except Exception as e:
        logger.error(f"Queue job failed: {e}", exc_info=True)
        result_text = f"Error: {str(e)}"

    try:
        db_pool = DBManager.get_pool()
        user_memory = UserMemoryManager(db_pool)
        repo = HistoryRepository(user_memory)

        data_state = await user_memory.load(chat_id)
        history = data_state["history"] if data_state else []
        telegram_username = data_state.get("telegram_name", "") if data_state else ""

        system_prompt = render_template("chat/queue_results_system.hbs", {})
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            last_user_msg = None
            for h in reversed(history):
                if h.get("role") == "user":
                    last_user_msg = h.get("text", "")
                    break
            if last_user_msg:
                messages.append({"role": "user", "content": last_user_msg})
                messages.append({"role": "assistant", "content": f"Queueing your song for {brand}..."})

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
        llm_result = await invoke_chat(llm_client=llm_client, messages=messages, return_full_history=True)
        reply = llm_result.actual_result

        await repo.update_from_result(chat_id, telegram_username, brand, history, llm_result)

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
        generated_tts_path: str,
        priority: int = 8,
        telegram_chat_id: Optional[int] = None
) -> Dict[str, Any]:

    if not brand or not song_uuid or not generated_tts_path:
        return {"success": False, "error": "brand, song_uuid, generated_tts_path are required"}

    op_id = uuid.uuid4().hex

    asyncio.create_task(
        _bg_queue_and_notify(
            brand,
            song_uuid,
            generated_tts_path,
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
            "description": "Generate a short intro via TTS and enqueue INTRO+SONG to the brand's radio queue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Brand slug"},
                    "song_uuid": {"type": "string", "description": "UUID of the selected song"},
                    "generated_tts_path": {"type": "string", "description": "Path to generated TTS file"},
                    "priority": {"type": "integer", "description": "Priority of the queue item", "minimum": 8, "maximum": 10, "default": 8},
                    "telegram_chat_id": {"type": "integer", "description": "Telegram chat ID"}
                },
                "required": ["brand", "song_uuid", "generated_tts_path", "telegram_chat_id"]
            }
        }
    }
