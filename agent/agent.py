import logging
import random
from typing import Dict, List

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from mcp.broadcaster_mcp_client import BroadcasterMCPClient

from tools.interaction_tools import InteractionTool
from tools.queue_tool import QueueTool
from tools.sound_fragment_tool import SoundFragmentTool


class AIDJAgent:
    def __init__(self, config: Dict, brand_config: Dict, language: str, api_client: BroadcasterAPIClient,
                 mcp_client=None):
        self.logger = logging.getLogger(__name__)
        self.brand_config = brand_config
        self.brand = brand_config.get('radioStationName')
        self.agent_config = brand_config.get('agent', {})

        # Use provided MCP client or create new one
        self.mcp_client = mcp_client if mcp_client else BroadcasterMCPClient(config)

        self.song_fetch_tool = SoundFragmentTool(config)
        self.api_client = api_client
        self.memory = InteractionMemory(
            brand=self.brand,
            api_client=self.api_client
        )

        # Pass MCP client to InteractionTool
        self.intro_tool = InteractionTool(
            config,
            self.memory,
            language,
            self.agent_config,
            self.brand,
            mcp_client=self.mcp_client
        )

        self.broadcast_tool = QueueTool(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self.language = language

        self._played_songs_history: List[str] = []
        self._cooldown_songs_count: int = self.agent_config.get('songCooldown', 4)

    async def run(self) -> None:
        self.logger.info(f"Starting DJ Agent run for brand: {self.brand}")
        self.logger.info(f"Agent name: {self.agent_config.get('name', 'Unknown')}")

        # Only connect if we created our own MCP client
        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.connect()

        await self._feed_broadcast_mcp()

        # Only disconnect if we created our own MCP client
        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")

    async def _feed_broadcast_mcp(self) -> None:
        try:
            audio_data, intro_reason, title, artist = await self.intro_tool.create_introduction(
                self.brand,
                agent_config=self.agent_config
            )

            if audio_data:
                # Extract song ID from intro_reason or use a placeholder
                song_id = "agent_selected"  # The agent will select the song via MCP tools
                if self.broadcast_tool.send_to_broadcast(self.brand, song_id, audio_data):
                    self.logger.info(f"Broadcasted with intro: {title} by {artist}")
            else:
                self.logger.warning(f"No audio generated. Reason: {intro_reason}")
        except Exception as e:
            self.logger.error(f"Error in _feed_broadcast_mcp: {e}")
            raise


def _select_song_from_fragments(self, fragments):
    playable_songs = [
        fragment['soundfragment'] for fragment in fragments
        if fragment['id'] not in self._played_songs_history
    ]

    if not playable_songs:
        self.logger.info("All available songs are currently in cooldown. Choosing randomly from all.")
        return random.choice([fragment['soundfragment'] for fragment in fragments])

    return random.choice(playable_songs)
