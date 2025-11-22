import logging
from typing import Dict

from elevenlabs import ElevenLabs

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from cnst.llm_types import LlmType
from models.live_container import LiveRadioStation
from tools.audio_processor import AudioProcessor
from tools.radio_dj_v2 import RadioDJV2


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

        self.memory = InteractionMemory(
            brand=self.brand,
            api_client=self.api_client
        )
        elevenlabs_inst = ElevenLabs(api_key=config.get("elevenlabs").get("api_key"))

        self.audio_processor = AudioProcessor(
            elevenlabs_inst,
            station,
            self.memory
        )

        from cnst.paths import MERGED_AUDIO_DIR
        self.radio_dj = RadioDJV2(
            station=station,
            audio_processor=self.audio_processor,
            target_dir=str(MERGED_AUDIO_DIR),
            llm_client=llm_client,
            llm_type=llm_type,
            db_pool=self.db_pool
        )

    async def run(self) -> None:
        self.logger.info(f"Starting DJ run for: {self.brand}, DJ: {self.live_station.djName}, Scene: {self.live_station.info}")

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