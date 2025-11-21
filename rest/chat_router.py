import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from llm.llm_request import invoke_chat
from repos.history_repo import HistoryRepository
from rest.app_setup import llm_factory, cfg
from rest.chat_request import ChatRequest
from util.template_loader import render_template

router = APIRouter()
logger = logging.getLogger(__name__)

API_KEY = cfg["web_handler"]["api_key"]


async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None):
    if x_api_key != API_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/chat/invoke", dependencies=[Depends(verify_api_key)])
async def chat_invoke(req: ChatRequest, request: Request):
    text = req.text
    brand = req.brand
    llm_choice = req.llm
    chat_id = req.chat_id
    telegram_username = req.telegram_username

    repo = HistoryRepository(request.app.state.user_memory)
    system_prompt = render_template(
        "chat/mixplaclone_system.hbs",
        {"brand": brand, "telegram_username": telegram_username}
    )
    messages, history, _ = await repo.build_messages(chat_id, system_prompt)
    messages.append({"role": "user", "content": text})

    client = llm_factory.get_llm_client(
        llm_choice,
        enable_sound_fragment_tool=True,
        enable_listener_tool=bool(telegram_username),
        enable_stations_tools=True
    )
    result = await invoke_chat(llm_client=client, messages=messages, return_full_history=True)
    reply = result.actual_result

    await repo.update_from_result(chat_id, telegram_username, brand, history, result, fallback_user_text=text)

    return {"ok": True, "brand": brand, "llm": llm_choice.name, "reply": reply}


@router.delete("/chat/clear", dependencies=[Depends(verify_api_key)])
async def chat_clear(chat_id: int, request: Request):
    repo = HistoryRepository(request.app.state.user_memory)
    await repo.clear(chat_id)
    return {"ok": True, "chat_id": chat_id}
