import logging
from typing import Annotated

import httpx
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine
from cnst.translation_types import TranslationType
from llm.llm_request import invoke_intro, invoke_chat, translate_content
from memory.brand_user_summorizer import BrandUserSummarizer
from rest.app_setup import app_lifespan, llm_factory, internet, sound_fragments, TELEGRAM_TOKEN, cors_settings, cfg
from rest.app_state import AppState
from rest.prompt_request import PromptRequest
from rest.chat_request import ChatRequest
from rest.search_request import SearchRequest
from rest.translation_request import TranslateRequest
from tools.radio_dj_v2 import RadioDJV2
from util.template_loader import render_template

logger = logging.getLogger(__name__)


logger.info("Initializing FastAPI application...")
app = FastAPI(lifespan=app_lifespan)
app.state = AppState()  # type: ignore
logger.info("FastAPI application initialized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_settings["allow_origins"],
    allow_methods=cors_settings["allow_methods"],
    allow_headers=["X-API-Key"] + cors_settings["allow_headers"],
)

API_KEY = cfg["web_handler"]["api_key"]

async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=404, detail="Resource not found")


@app.get("/health", dependencies=[Depends(verify_api_key)])
def health():
    return {"status": "ok"}


@app.post("/telegram/webhook")
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

    data_state = await app.state.user_memory.load(chat_id)
    history = data_state["history"] if data_state else []
    
    messages = [{"role": "system", "content": "You are Mixplaclone, a helpful assistant of the radio station, chatting privately with a listener."}]
    
    for h in history[-19:]:  # Leave room for current message
        role = "assistant" if h.get("role") == "assistant" else "user"
        content = h.get("text", "")
        if content:
            messages.append({"role": role, "content": content})
    
    messages.append({"role": "user", "content": text})
    
    client = llm_factory.get_llm_client(LlmType.GROQ, internet_mcp=internet, sound_fragment_mcp=sound_fragments)
    result = await invoke_chat(llm_client=client, messages=messages)
    reply = result.actual_result

    if not data_state:
        history = [{"role": "user", "text": text}, {"role": "assistant", "text": reply}]
    else:
        history.extend([{"role": "user", "text": text}, {"role": "assistant", "text": reply}])
        history = history[-50:]  # Keep last 50 messages (25 exchanges)
    await app.state.user_memory.save(chat_id, name, brand, history)

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}


@app.post("/internet_search/test", dependencies=[Depends(verify_api_key)])
async def test_search(req: SearchRequest):
    logger.info(f"REQ llm={req.llm.name} prompt_len={len(req.prompt)}")
    q = req.prompt or ""
    max_results = 3
    results_out = []
    if req.searchEngine == SearchEngine.Perplexity:
        pdata = await internet.ask_perplexity(q, max_items=max_results)
        for s in pdata.get("items", [])[:max_results]:
            results_out.append(s)
    else:
        data = await internet.search_internet(q, max_results=max_results)
        results = data.get("results", []) if isinstance(data, dict) else []
        for it in results[:max_results]:
            results_out.append(it.get("snippet", ""))
    return {"results": results_out, "llm": req.llm.name}


@app.post("/translate", dependencies=[Depends(verify_api_key)])
async def translate(req: TranslateRequest):
    client = llm_factory.get_llm_client(LlmType.GROQ)

    template_path = "translation/prompt.hbs" if req.translationType == TranslationType.PROMPT else "translation/code.hbs"
    to_translate_text = render_template(template_path, {
        "language": req.language,
        "toTranslate": req.toTranslate
    })

    translation_result = await translate_content(client, to_translate_text)
    return {"result": translation_result.actual_result, "reasoning": translation_result.reasoning}


@app.post("/prompt/test", dependencies=[Depends(verify_api_key)])
async def test_prompt(req: PromptRequest):
    client = llm_factory.get_llm_client(req.llm, internet_mcp=internet)

    result = await invoke_intro(client, req.prompt, req.draft, "")
    print(f" >>>> RAW: {result}")
    return {"result": result.actual_result, "reasoning": result.reasoning}


@app.post("/chat/test", dependencies=[Depends(verify_api_key)])
async def chat_test(req: ChatRequest):
    text = req.text
    brand = req.brand or "default"
    llm_choice = req.llm

    messages = [
        {"role": "system", "content": f"You are Mixplaclone, a helpful assistant of the radio station. Brand context: '{brand}'. When asked for music, call the tool get_brand_sound_fragment with brand '{brand}' and fragment_type 'SONG'."},
        {"role": "user", "content": text}
    ]

    client = llm_factory.get_llm_client(llm_choice, internet_mcp=internet, sound_fragment_mcp=sound_fragments)
    result = await invoke_chat(llm_client=client, messages=messages)
    reply = result.actual_result

    return {"ok": True, "brand": brand, "llm": llm_choice.name, "reply": reply}


@app.post("/debug/summarize/{brand}", dependencies=[Depends(verify_api_key)])
async def debug_summarize(brand: str):
    result = await app.state.summarizer.summarize(brand)
    return {"summary": result}


@app.get("/debug/brand_memory", dependencies=[Depends(verify_api_key)])
async def debug_brand_memory():
    return RadioDJV2.memory_manager.memory

@app.get("/debug/user_memory", dependencies=[Depends(verify_api_key)])
async def debug_user_memory():
    return await app.state.user_memory.get_all()

@app.get("/debug/listener_summary/{brand}", dependencies=[Depends(verify_api_key)])
async def debug_listener_summary(brand: str):
    summarizer = BrandUserSummarizer(
        app.state.db,
        llm_factory.get_llm_client(LlmType.GROQ),
        LlmType.GROQ
    )
    return {"summary": await summarizer.summarize(brand)}
