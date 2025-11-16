import logging
import asyncpg
import httpx
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

# Import application components
from rest.app_state import AppState
from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine
from cnst.translation_types import TranslationType
from core.config import get_merged_config
from llm.llm_request import invoke_intro, translate_content
from mcp.external.internet_mcp import InternetMCP
from memory.brand_summarizer import BrandSummarizer
from memory.brand_user_summorizer import BrandUserSummarizer
from memory.brans_memory_manager import BrandMemoryManager
from memory.user_memory_manager import UserMemoryManager
from tools.radio_dj_v2 import RadioDJV2
from util.llm_factory import LlmFactory
from util.template_loader import render_template

# Load configuration
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

# Initialize services
llm_factory = LlmFactory(cfg)
internet = InternetMCP(config=cfg)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application lifespan...")
    pool = None
    try:
        # Resolve DSN and SSL
        env_dsn = os.getenv("DATABASE_URL") or os.getenv("DB_DSN")
        effective_dsn = env_dsn or DB_DSN
        if not effective_dsn:
            logger.error("No database DSN provided (missing config and env DATABASE_URL/DB_DSN)")
            raise RuntimeError("Missing database DSN")

        db_cfg_local = cfg.get("database", {})
        ssl_required = bool(db_cfg_local.get("ssl", False) or os.getenv("DB_SSL") in {"1", "true", "True"})

        # Log configuration
        source = "env" if env_dsn else "config"
        logger.info(f"Using {source} DSN (first 20 chars): {effective_dsn[:20]}... | SSL: {ssl_required}")
        
        # Initialize database pool
        logger.info("Initializing database connection pool...")
        attempts = 5
        delay = 3
        last_exc = None
        for i in range(1, attempts + 1):
            try:
                pool = await asyncpg.create_pool(effective_dsn, ssl=True if ssl_required else None)
                break
            except Exception as e:
                last_exc = e
                logger.error(f"DB pool creation attempt {i}/{attempts} failed: {e}")
                if i < attempts:
                    await asyncio.sleep(delay)
        if not pool and last_exc:
            raise last_exc
        if pool:
            logger.info("Database pool created successfully")
            app.state.db = pool
        else:
            logger.error("Failed to create database pool")
            raise RuntimeError("Failed to create database pool")
        
        # Initialize services
        logger.info("Initializing BrandMemoryManager...")
        app.state.brand_memory = BrandMemoryManager()
        
        logger.info("Initializing UserMemoryManager...")
        app.state.user_memory = UserMemoryManager(pool)
        
        logger.info("Initializing BrandSummarizer...")
        app.state.summarizer = BrandSummarizer(
            llm_client=llm_factory.get_llm_client(LlmType.GROQ),
            db_pool=pool,
            memory_manager=RadioDJV2.memory_manager,
            llm_type=LlmType.GROQ
        )
        
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}", exc_info=True)
        raise
        
    finally:
        logger.info("Shutting down application...")
        if pool:
            logger.info("Closing database pool...")
            await pool.close()
            logger.info("Database pool closed")

# Initialize FastAPI app
logger.info("Initializing FastAPI application...")
app = FastAPI(lifespan=lifespan)
app.state = AppState()  # type: ignore
logger.info("FastAPI application initialized")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)


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



@app.post("/telegram/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    msg = data.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")
    name = chat.get("username") or chat.get("first_name") or ""
    brand = "default"

    if not chat_id or not text:
        return {"ok": False}

    await app.state.user_memory.add(chat_id, name, brand, text)

    summarizer = BrandUserSummarizer(
        app.state.db,
        llm_factory.get_llm_client(LlmType.GROQ),
        LlmType.GROQ
    )
    listener_summary = await summarizer.summarize(brand)

    result = await invoke_intro(
        llm_client=llm_factory.get_llm_client(LlmType.GROQ),
        prompt=f"Reply warmly as a DJ speaking privately to the listener.\nListener summary:\n{listener_summary}",
        draft=text,
        llm_type=LlmType.GROQ
    )
    reply = result.actual_result.replace("<result>", "").replace("</result>", "").strip()

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

@app.post("/debug/summarize/{brand}")
async def debug_summarize(brand: str):
    result = await app.state.summarizer.summarize(brand)
    return {"summary": result}

@app.get("/debug/brand_memory")
async def debug_brand_memory():
    return RadioDJV2.memory_manager.memory

# debug: view current listener summary
@app.get("/debug/listener_summary/{brand}")
async def debug_listener_summary(brand: str):
    summarizer = BrandUserSummarizer(
        app.state.db,
        llm_factory.get_llm_client(LlmType.GROQ),
        LlmType.GROQ
    )
    return {"summary": await summarizer.summarize(brand)}



