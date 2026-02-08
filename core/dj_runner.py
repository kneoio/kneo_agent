import logging
from typing import Dict

from api.broadcaster_client import BroadcasterAPIClient
from cnst.llm_types import LlmType
from models.live_container import LiveRadioStation
from tools.audio_processor import AudioProcessor
from tools.radio_dj_v2 import RadioDJV2
from tts.tts_factory import TTSEngineFactory


class DJRunner:
    def __init__(self, config: Dict, station: LiveRadioStation, api_client: BroadcasterAPIClient,
                 llm_client=None, llm_type=LlmType.GROQ, db_pool=None):
        if db_pool is None:
            raise ValueError("db_pool parameter is required for DJRunner initialization")

        self.logger = logging.getLogger(__name__)
        self.live_station = station
        self.brand = station.name
        self.api_client = api_client
        self.db_pool = db_pool

        tts_engine_type = station.tts.ttsEngineType
        if not tts_engine_type:
            self.logger.error(f"Station {station.name} has no ttsEngineType configured")
            raise ValueError(f"Station {station.name} has no ttsEngineType configured")

        tts_engine = TTSEngineFactory.create_engine(tts_engine_type, config)

        self.audio_processor = AudioProcessor(
            tts_engine,
            station,
            None
        )

        from cnst.paths import MERGED_AUDIO_DIR
        log_directory = config.get("logging", {}).get("directory", "logs")
        self.radio_dj = RadioDJV2(
            station=station,
            audio_processor=self.audio_processor,
            target_dir=str(MERGED_AUDIO_DIR),
            llm_client=llm_client,
            llm_type=llm_type,
            db_pool=self.db_pool,
            log_directory=log_directory
        )

    async def run(self) -> None:
        self.logger.info(
            f"Starting DJ run for: {self.brand}, DJ: {self.live_station.djName}, Scene: {self.live_station.info}")

        try:
            broadcast_success, _, _ = await self.radio_dj.run()
            if broadcast_success:
                self.logger.info(f"Successfully broadcasted intro for: {self.brand}")
            else:
                self.logger.warning(f"Broadcast failed for: {self.brand}")
        except Exception as e:
            self.logger.error(f"Error in radio_dj_v2 run: {e}")
            raise

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")

    async def cleanup(self):
        return
