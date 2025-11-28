import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from core.config import load_config
from mcp.external.internet_mcp import InternetMCP
from util.db_manager import DBManager
from util.llm_factory import LlmFactory

logger = logging.getLogger(__name__)

cfg: Dict = load_config("config.yaml")
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

_audio_processor = None

def get_audio_processor():
    return _audio_processor


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info("Starting application lifespan...")
    try:
        logger.info("Initializing database connection...")
        await DBManager.init()
        app.state.db = DBManager.get_pool()

        logger.info("Initializing AudioProcessor for queue tool...")
        try:
            from elevenlabs.client import ElevenLabs
            from tools.audio_processor import AudioProcessor
            global _audio_processor
            elevenlabs_cfg = cfg.get("elevenlabs", {})
            elevenlabs_client = ElevenLabs(api_key=elevenlabs_cfg.get("api_key"))
            _audio_processor = AudioProcessor(elevenlabs_client, None, None)
            app.state.audio_processor = _audio_processor
            logger.info("AudioProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AudioProcessor: {e}", exc_info=True)
            logger.warning("Queue tool will not be available")

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
