import logging
from typing import Dict, List

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from mcp.broadcaster_mcp_client import BroadcasterMCPClient

from tools.radio_dj_agent import RadioDJAgent
from api.queue import Queue
from tools.sound_fragment_tool import SoundFragmentTool


class DJRunner:
    def __init__(self, config: Dict, brand_config: Dict, api_client: BroadcasterAPIClient,
                 mcp_client=None):
        self.logger = logging.getLogger(__name__)
        self.brand_config = brand_config
        self.brand = brand_config.get('radioStationName')
        self.agent_config = brand_config.get('agent', {})
        self.mcp_client = mcp_client if mcp_client else BroadcasterMCPClient(config)
        self.song_fetch_tool = SoundFragmentTool(config)
        self.api_client = api_client
        self.memory = InteractionMemory(
            brand=self.brand,
            api_client=self.api_client
        )

        self.radio_dj_agent = RadioDJAgent(
            config,
            self.memory,
            self.agent_config,
            self.brand,
            mcp_client=self.mcp_client
        )

        self.broadcast_tool = Queue(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self._played_songs_history: List[str] = []
        self._cooldown_songs_count: int = self.agent_config.get('songCooldown', 4)

    async def run(self) -> None:
        self.logger.info(f"Starting DJ Agent run for brand: {self.brand}")
        self.logger.info(f"Agent name: {self.agent_config.get('name')}")

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.connect()

        await self._feed_broadcast()

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")

    async def _feed_broadcast(self) -> None:
        try:
            audio_data, song_id, title, artist = await self.radio_dj_agent.create_introduction(
                brand=self.brand
            )

            if audio_data:
                if self.broadcast_tool.send_to_broadcast(self.brand, song_id, audio_data):
                    self.logger.info(f"Broadcasted with intro: {title} by {artist}")
            else:
                self.logger.warning(f"No audio generated")
        except Exception as e:
            self.logger.error(f"Error in _feed_broadcast_mcp: {e}")
            raise
