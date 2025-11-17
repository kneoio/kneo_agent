import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from core.config import get_merged_config
from cnst.llm_types import LlmType
from memory.brans_memory_manager import BrandMemoryManager
from memory.user_memory_manager import UserMemoryManager
from memory.brand_summarizer import BrandSummarizer
from tools.radio_dj_v2 import RadioDJV2
from util.llm_factory import LlmFactory
from util.db_manager import DBManager
from mcp.external.internet_mcp import InternetMCP

logger = logging.getLogger(__name__)

cfg: Dict = get_merged_config("config.yaml")
telegram_cfg = cfg.get("telegram", {})
TELEGRAM_TOKEN: str = telegram_cfg.get("token", "")
server_cfg = cfg.get("web_server", {})
cors_cfg = server_cfg.get("cors", {})

cors_settings = {
    "allow_origins": cors_cfg.get("allow_origins", ["*"]),
    "allow_methods": cors_cfg.get("allow_methods", ["*"]),
    "allow_headers": cors_cfg.get("allow_headers", ["*"])
}

llm_factory = LlmFactory(cfg)
internet = InternetMCP(config=cfg)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info("Starting application lifespan...")
    try:
        logger.info("Initializing database connection...")
        await DBManager.init()
        app.state.db = DBManager.get_pool()

        logger.info("Initializing BrandMemoryManager...")
        app.state.brand_memory = BrandMemoryManager()

        logger.info("Initializing UserMemoryManager...")
        app.state.user_memory = UserMemoryManager(app.state.db)

        logger.info("Initializing BrandSummarizer...")
        app.state.summarizer = BrandSummarizer(
            llm_client=llm_factory.get_llm_client(LlmType.GROQ),
            db_pool=app.state.db,
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
        try:
            await DBManager.close()
            logger.info("Database pool closed")
        except Exception as e:
            logger.warning(f"Error during DB pool close: {e}")
