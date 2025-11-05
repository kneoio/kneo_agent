import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine
from core.config import get_merged_config
from llm.llm_request import invoke_intro
from mcp.external.internet_mcp import InternetMCP
from util.llm_factory import LlmFactory

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


class SearchRequest(BaseModel):
    prompt: str
    llm: LlmType
    searchEngine: SearchEngine = SearchEngine.Brave


class PromptRequest(BaseModel):
    prompt: str
    draft: str
    llm: LlmType


@app.get("/health")
def health():
    return {"status": "ok"}


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

@app.post("/prompt/test")
async def test_prompt(req: PromptRequest):
    client = llm_factory.get_llm_client(req.llm, internet_mcp=internet)
    
    result = await invoke_intro(client, req.prompt, req.draft, req.llm)
    return {"result": result.actual_result, "reasoning": result.reasoning}

