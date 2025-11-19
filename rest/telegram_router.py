import logging
import httpx
from fastapi import APIRouter, Request

from cnst.llm_types import LlmType
from llm.llm_request import invoke_chat
from rest.app_setup import llm_factory, TELEGRAM_TOKEN
from util.template_loader import render_template

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    msg = data.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")
    name = chat.get("username") or chat.get("first_name") or ""
    brand = "default"

    preview = text if len(text) <= 120 else text[:117] + "..."
    logger.info(f"Telegram webhook: received chat_id={chat_id}, name={name}, text='{preview}'")

    app = req.app
    data_state = await app.state.user_memory.load(chat_id)
    history = data_state["history"] if data_state else []

    system_prompt = render_template("chat/mixplaclone_system.hbs", {"brand": brand})
    messages = [{"role": "system", "content": system_prompt}]

    for h in history[-19:]:
        role = "assistant" if h.get("role") == "assistant" else "user"
        content = h.get("text", "")
        if content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": text})

    client = llm_factory.get_llm_client(LlmType.GROQ, enable_sound_fragment_tool=True)
    result = await invoke_chat(llm_client=client, messages=messages)
    reply = result.actual_result

    if not data_state:
        history = [{"role": "user", "text": text}, {"role": "assistant", "text": reply}]
    else:
        history.extend([{"role": "user", "text": text}, {"role": "assistant", "text": reply}])
        history = history[-50:]
    await app.state.user_memory.save(chat_id, name, brand, history)

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}
