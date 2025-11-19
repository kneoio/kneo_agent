import logging
import httpx
import asyncio
from fastapi import APIRouter, Request, BackgroundTasks

from cnst.llm_types import LlmType
from llm.llm_request import invoke_chat
from rest.app_setup import llm_factory, TELEGRAM_TOKEN
from util.template_loader import render_template

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_telegram_message(chat_id: int, text: str, name: str, brand: str, app):
    data_state = await app.state.user_memory.load(chat_id)
    history = data_state["history"] if data_state else []

    system_prompt = render_template("chat/mixplaclone_system.hbs", {"brand": brand})
    messages = [{"role": "system", "content": system_prompt}]

    for h in history[-19:]:
        role = h.get("role")
        if role == "user":
            content = h.get("text", "")
            if content:
                messages.append({"role": "user", "content": content})
        elif role == "assistant":
            content = h.get("text", "")
            tool_calls = h.get("tool_calls")
            if content or tool_calls:
                messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})
        elif role == "tool":
            messages.append({
                "role": "tool",
                "name": h.get("name"),
                "content": h.get("content", ""),
                "tool_call_id": h.get("tool_call_id")
            })

    messages.append({"role": "user", "content": text})

    client = llm_factory.get_llm_client(LlmType.GROQ, enable_sound_fragment_tool=True)
    result = await invoke_chat(llm_client=client, messages=messages, return_full_history=True)
    reply = result.actual_result

    if result.full_messages:
        new_history = []
        for msg in result.full_messages:
            role = msg.get("role")
            if role == "system":
                continue
            if role == "user":
                new_history.append({"role": "user", "text": msg.get("content", "")})
            elif role == "assistant":
                new_history.append({"role": "assistant", "text": msg.get("content", ""), "tool_calls": msg.get("tool_calls")})
            elif role == "tool":
                new_history.append({"role": "tool", "name": msg.get("name"), "content": msg.get("content"), "tool_call_id": msg.get("tool_call_id")})
        
        if not data_state:
            history = new_history
        else:
            history.extend(new_history)
            history = history[-50:]
    else:
        if not data_state:
            history = [{"role": "user", "text": text}, {"role": "assistant", "text": reply}]
        else:
            history.extend([{"role": "user", "text": text}, {"role": "assistant", "text": reply}])
            history = history[-50:]
    
    await app.state.user_memory.save(chat_id, name, brand, history)

    async with httpx.AsyncClient() as http_client:
        await http_client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )


@router.post("/telegram/webhook")
async def telegram_webhook(req: Request, background_tasks: BackgroundTasks):
    data = await req.json()
    msg = data.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")
    name = chat.get("username") or chat.get("first_name") or ""
    brand = "default"

    if not text:
        logger.info(f"Telegram webhook: non-text update received for chat_id={chat_id}; skipping")
        return {"ok": True}

    preview = text if len(text) <= 120 else text[:117] + "..."
    logger.info(f"Telegram webhook: received chat_id={chat_id}, name={name}, text='{preview}'")

    background_tasks.add_task(process_telegram_message, chat_id, text, name, brand, req.app)

    return {"ok": True}
