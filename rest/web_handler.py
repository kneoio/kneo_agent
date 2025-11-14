import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine
from cnst.translation_types import TranslationType
from core.config import get_merged_config
from llm.llm_request import invoke_intro
from llm.llm_request import translate_content
from mcp.external.internet_mcp import InternetMCP
from util.llm_factory import LlmFactory
from util.template_loader import render_template

import asyncpg
import httpx
from fastapi import Request

app = FastAPI()
logger = logging.getLogger(__name__)
 
cfg = get_merged_config("config.yaml")
telegram_cfg = cfg.get("telegram", {})
db_cfg = cfg.get("database", {})
TELEGRAM_TOKEN = telegram_cfg.get("token")
DB_DSN = db_cfg.get("dsn")
server_cfg = cfg.get("mcp_server", {})
cors_cfg = server_cfg.get("cors", {})
allow_origins = cors_cfg.get("allow_origins", ["*"])
allow_methods = cors_cfg.get("allow_methods", ["*"])
allow_headers = cors_cfg.get("allow_headers", ["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)

llm_factory = LlmFactory(cfg)
internet = InternetMCP(config=cfg)


class SearchRequest(BaseModel):
    prompt: str
    llm: LlmType
    searchEngine: SearchEngine = SearchEngine.Brave


class PromptRequest(BaseModel):
    prompt: str
    draft: str
    llm: LlmType

class TranslateRequest(BaseModel):
    toTranslate: str
    translationType: TranslationType
    language: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(DB_DSN)

@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")

    if not chat_id or not text:
        return {"ok": False, "reason": "no message"}

    async with app.state.db.acquire() as conn:
        await conn.execute("""
            INSERT INTO mixpla__chat_log (author, reg_date, last_mod_user, last_mod_date, brand, data)
            VALUES ($1, NOW(), $1, NOW(), 'default', jsonb_build_array(jsonb_build_object('role','user','text',$2)))
            ON CONFLICT (author)
            DO UPDATE SET
                data = mixpla__chat_log.data || jsonb_build_array(jsonb_build_object('role','user','text',$2)),
                last_mod_date = NOW();
        """, chat_id, text)

    reply = f"Got your message: {text}"
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}

@app.post("/internet_search/test")
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


@app.post("/translate")
async def translate(req: TranslateRequest):
    client = llm_factory.get_llm_client(LlmType.GROQ)
    
    template_path = "translation/prompt.hbs" if req.translationType == TranslationType.PROMPT else "translation/code.hbs"
    to_translate_text = render_template(template_path, {
        "language": req.language,
        "toTranslate": req.toTranslate
    })

    translation_result = await translate_content(client, to_translate_text)
    # print(f"RAW: {translation_result}")
    return {"result": translation_result.actual_result, "reasoning": translation_result.reasoning}

@app.post("/prompt/test")
async def test_prompt(req: PromptRequest):
    client = llm_factory.get_llm_client(req.llm, internet_mcp=internet)
    
    result = await invoke_intro(client, req.prompt, req.draft, req.llm)
    print(f" >>>> RAW: {result}")
    return {"result": result.actual_result, "reasoning": result.reasoning}

