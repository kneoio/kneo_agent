import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cnst.llm_types import LlmType
from core.config import get_merged_config
from mcp.external.internet_mcp import InternetMCP
from mcp.server.llm_response import LlmResponse
from util.llm_factory import LlmFactory, generate_dj_intro_text

app = FastAPI()
logger = logging.getLogger(__name__)

cfg = get_merged_config("config.yaml")
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


class PromptRequest(BaseModel):
    prompt: str
    llm: LlmType


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/internet_search/test")
async def test_prompt(req: PromptRequest):
    logger.info(f"REQ llm={req.llm.name} prompt_len={len(req.prompt)}")
    q = req.prompt or ""
    max_results = 3
    data = await internet.search_internet(q, max_results=max_results)
    results = data.get("results", []) if isinstance(data, dict) else []
    items = []
    for it in results[:max_results]:
        items.append({
            "title": it.get("title", ""),
            "snippet": it.get("snippet", "")
        })
    return {"items": items, "llm": req.llm.name}


@app.post("/radio_dj/test/{llm}")
async def radio_dj_test_auto(llm: LlmType, request: Request):
    ct = request.headers.get("content-type", "")
    client = llm_factory.get_llm_client(llm, internet_mcp=internet)
    vars = {}

    if ct.startswith("text/plain"):
        raw = await request.body()
        song_prompt = raw.decode("utf-8")
    elif ct.startswith("application/json"):
        data = await request.json()
        vars = data.get("variables", {})  # Fixed typo: "varibales" -> "variables"
        song_prompt = data.get("template", "")
        print(song_prompt)
    else:
        song_prompt = ""

    # Extract all required variables with defaults
    dj_name = vars.get("ai_dj_name", "")
    context = vars.get("context", "")
    brand = vars.get("brand", "")
    events = vars.get("events", "")
    title = vars.get("title", "")
    artist = vars.get("artist", "")
    genres = vars.get("genres", [])
    history = vars.get("history", [])
    listeners = vars.get("listeners", [])
    instant_message = vars.get("instant_message", [])

    resp = await generate_dj_intro_text(
        client,
        song_prompt,
        dj_name,
        context,
        brand,
        events,
        title,
        artist,
        genres,
        history,
        listeners,
        instant_message
    )

    standardized_resp = LlmResponse.from_response(resp, llm)
    return standardized_resp.model_dump()

