import logging
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI

from core.config import load_config
from cnst.llm_types import LlmType
from memory.brand_memory_manager import BrandMemoryManager
from memory.user_memory_manager import UserMemoryManager
from memory.brand_summarizer import BrandSummarizer
from tools.radio_dj_v2 import RadioDJV2
from util.llm_factory import LlmFactory
from util.db_manager import DBManager
from mcp.external.internet_mcp import InternetMCP
from api.stations_api import StationsAPI
from api.listener_api import ListenerAPI

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

        logger.info("Initializing BrandMemoryManager...")
        app.state.brand_memory = BrandMemoryManager()

        logger.info("Initializing UserMemoryManager...")
        app.state.user_memory = UserMemoryManager(app.state.db)

        logger.info("Initializing ListenerAPI...")
        app.state.listener_api = ListenerAPI(cfg)
        from tools.listener_tool import set_listener_api
        set_listener_api(app.state.listener_api)

        logger.info("Initializing StationsAPI...")
        app.state.stations_api = StationsAPI(cfg)
        from tools.stations_tool import set_stations_api
        set_stations_api(app.state.stations_api)

        logger.info("Initializing BrandSummarizer...")
        app.state.summarizer = BrandSummarizer(
            llm_client=llm_factory.get_llm_client(LlmType.GROQ),
            db_pool=app.state.db,
            memory_manager=RadioDJV2.memory_manager,
            llm_type=LlmType.GROQ
        )

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

        logger.info("Starting ConversationSummarizer...")
        from memory.conversation_summarizer import ConversationSummarizer
        import asyncio
        app.state.conversation_summarizer = ConversationSummarizer(
            user_memory_manager=app.state.user_memory,
            llm_factory=llm_factory,
            interval_minutes=30,
            idle_threshold_minutes=30
        )
        
        logger.info("Running initial conversation summarization check...")
        await app.state.conversation_summarizer._check_and_summarize_conversations()
        
        app.state.summarizer_task = asyncio.create_task(app.state.conversation_summarizer.start())
        logger.info("ConversationSummarizer started")

        logger.info("Application startup completed successfully")
        yield
        
        logger.info("Stopping ConversationSummarizer...")
        await app.state.conversation_summarizer.stop()
        app.state.summarizer_task.cancel()
        try:
            await app.state.summarizer_task
        except asyncio.CancelledError:
            pass

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
