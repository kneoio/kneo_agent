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
                 mcp_client=None, llm_client=None, llm_type=LlmType.GROQ):
        self.logger = logging.getLogger(__name__)
        self.live_station = station
        self.brand = station.name
        self.mcp_client = mcp_client
        self.api_client = api_client

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

        self.radio_dj = RadioDJV2(
            station,
            self.audio_processor,
            mcp_client=self.mcp_client,
            llm_client=llm_client,
            llm_type=llm_type
        )

    async def run(self) -> None:
        self.logger.info(f"Starting DJ run for: {self.brand}, DJ: {self.live_station.djName}, Scene: {self.live_station.info}")

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.connect()

        try:
            broadcast_success, _, _ = await self.radio_dj.run()
            if broadcast_success:
                self.logger.info(f"Successfully broadcasted intro for: {self.brand}")
            else:
                self.logger.warning(f"Broadcast failed for: {self.brand}")
        except Exception as e:
            self.logger.error(f"Error in _feed_broadcast: {e}")
            raise
        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")


    async def cleanup(self):
        if hasattr(self, 'mcp_client') and not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()