import logging
import httpx
from fastapi import APIRouter, Request
from cnst.llm_types import LlmType
from llm.llm_request import invoke_chat
from rest.app_setup import llm_factory, TELEGRAM_TOKEN
from util.template_loader import render_template
from repos.history_repo import HistoryRepository

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    msg = data.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")
    telegram_username = chat.get("username") or ""
    brand = "default"

    if not text:
        logger.info(f"Telegram webhook: non-text update received for chat_id={chat_id}; skipping")
        return {"ok": True}

    preview = text if len(text) <= 120 else text[:117] + "..."
    logger.info(f"Telegram webhook: received chat_id={chat_id}, name={telegram_username}, text='{preview}'")

    repo = HistoryRepository(req.app.state.user_memory)
    system_prompt = render_template("chat/mixplaclone_system.hbs", {
        "brand": brand,
        "telegram_username": telegram_username
    })
    messages, history, _ = await repo.build_messages(chat_id, system_prompt)
    messages.append({"role": "user", "content": text})

    forced_llm = LlmType.CLAUDE
    # forced_llm = LlmType.GROQ
    client = llm_factory.get_llm_client(
        forced_llm,
        enable_sound_fragment_tool=True,
        enable_listener_tool=True,
        enable_stations_tools=True
    )
    result = await invoke_chat(llm_client=client, messages=messages, return_full_history=True)
    reply = result.actual_result

    await repo.update_from_result(chat_id, telegram_username, brand, history, result, fallback_user_text=text)

    async with httpx.AsyncClient() as http_client:
        await http_client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}
