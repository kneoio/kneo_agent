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
    try:
        data = await req.json()
        logger.info(f"Telegram webhook received: {data}")
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
        t = text.strip().lower()
        if t in "/reset":
            await repo.clear(chat_id)
            async with httpx.AsyncClient() as http_client:
                await http_client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": "History cleared."}
                )
            return {"ok": True}
        
        from datetime import datetime, timedelta
        data_state = await req.app.state.user_memory.load(chat_id)
        if data_state and data_state.get("last_mod_date"):
            time_since_activity = datetime.now() - data_state["last_mod_date"]
            if time_since_activity > timedelta(minutes=30):
                logger.info(f"Chat {chat_id} returning after {time_since_activity.total_seconds()/60:.1f}min idle, summarizing...")
                await req.app.state.conversation_summarizer._summarize_conversation(chat_id)
        
        system_prompt = render_template("chat/mixplaclone_system.hbs", {
            "brand": brand,
            "telegram_username": telegram_username,
            "telegram_chat_id": chat_id
        })
        messages, history, _ = await repo.build_messages(chat_id, system_prompt)
        messages.append({"role": "user", "content": text})

        forced_llm = LlmType.GROQ
        client = llm_factory.get_llm_client(
            forced_llm,
            enable_sound_fragment_tool=True,
            enable_listener_tool=True,
            enable_stations_tools=True,
            enable_queue_tool=True
        )
        result = await invoke_chat(llm_client=client, messages=messages, return_full_history=True)
        reply = result.actual_result

        if not reply or not reply.strip():
            logger.warning(f"Empty LLM response for chat_id={chat_id}, using fallback")
            reply = "I'm processing your request but encountered an issue. Could you try rephrasing?"

        await repo.update_from_result(chat_id, telegram_username, brand, history, result, fallback_user_text=text)

        async with httpx.AsyncClient() as http_client:
            telegram_response = await http_client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
            if telegram_response.status_code != 200:
                logger.error(f"Telegram API error: {telegram_response.status_code} - {telegram_response.text}")
                logger.error(f"Failed message content (len={len(reply)}): {repr(reply[:200])}")

        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
