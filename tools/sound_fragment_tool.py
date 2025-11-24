import asyncio
import uuid
from typing import Dict, Any, Optional

import httpx

from api.sound_fragment_api import BrandSoundFragmentsAPI
from core.config import load_config

import logging
logger = logging.getLogger(__name__)

TEST_CHAT_ID = 123

async def _bg_fetch_and_push(
        brand: str,
        keyword: Optional[str],
        limit: Optional[int],
        offset: Optional[int],
        chat_id: int,
        operation_id: str
):
    from util.db_manager import DBManager
    from memory.user_memory_manager import UserMemoryManager
    from repos.history_repo import HistoryRepository
    from llm.llm_request import invoke_chat
    from rest.app_setup import llm_factory, TELEGRAM_TOKEN
    from cnst.llm_types import LlmType
    from util.template_loader import render_template

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

    except Exception as e:
        logger.error(f"Search API error: {e}", exc_info=True)
        results_text = f"Error: {str(e)}"

    try:
        db_pool = DBManager.get_pool()
        user_memory = UserMemoryManager(db_pool)
        repo = HistoryRepository(user_memory)

        data_state = await user_memory.load(chat_id)
        history = data_state["history"] if data_state else []
        telegram_username = data_state.get("telegram_name", "") if data_state else ""

        system_prompt = render_template("chat/search_results_system.hbs", {})
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            last_user_msg = None
            for h in reversed(history):
                if h.get("role") == "user":
                    last_user_msg = h.get("text", "")
                    break
            if last_user_msg:
                messages.append({"role": "user", "content": last_user_msg})
                action = f"Searching for '{keyword}'" if keyword else "Fetching latest songs"
                messages.append({"role": "assistant", "content": f"{action} in {brand}..."})

        messages.append({
            "role": "user",
            "content": f"Here are the search results:\n\n{results_text}"
        })

        client = llm_factory.get_llm_client(
            LlmType.GROQ,
            enable_sound_fragment_tool=False,
            enable_listener_tool=False,
            enable_stations_tools=False
        )
        llm_result = await invoke_chat(llm_client=client, messages=messages, return_full_history=True)
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
        import logging
        logging.error(f"Error in _bg_fetch_and_push LLM trigger: {e}")


async def get_brand_sound_fragment(
        brand: str,
        keyword: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        telegram_chat_id: Optional[int] = None
) -> Dict[str, Any]:
    op_id = uuid.uuid4().hex

    asyncio.create_task(
        _bg_fetch_and_push(
            brand,
            keyword,
            limit,
            offset,
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
            "name": "get_brand_sound_fragment",
            "description": "Search or browse brand sound fragments. If keyword is empty/missing, returns latest songs for browsing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Brand slug"},
                    "keyword": {"type": "string", "description": "Search keyword. Leave empty to browse latest songs."},
                    "limit": {"type": "integer", "description": "Maximum number of results"},
                    "offset": {"type": "integer", "description": "Offset for pagination"},
                    "telegram_chat_id": {"type": "integer", "description": "Telegram chat ID"}
                },
                "required": ["brand", "telegram_chat_id"]
            }
        }
    }
