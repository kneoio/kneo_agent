import logging
import random
from typing import Dict, List
from elevenlabs import ElevenLabs
from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from api.queue import Queue
from core.prerecorded import Prerecorded
from mcp.broadcaster_mcp_client import BroadcasterMCPClient
from tools.audio_processor import AudioProcessor
from tools.radio_dj_agent import RadioDJAgent
from api.sound_fragment import SoundFragment


class DJRunner:
    def __init__(self, config: Dict, brand_config: Dict, api_client: BroadcasterAPIClient,
                 mcp_client=None, llmClient=None):
        self.logger = logging.getLogger(__name__)
        self.brand_config = brand_config
        self.brand = brand_config.get('radioStationName')
        self.agent_config = brand_config.get('agent', {})
        self.talkativity = self.agent_config.get('talkativity', 0.3)
        self.mcp_client = mcp_client if mcp_client else BroadcasterMCPClient(config)
        self.song_fetch_tool = SoundFragment(config)
        self.api_client = api_client

        self.memory = InteractionMemory(
            brand=self.brand,
            api_client=self.api_client
        )
        elevenlabs_inst = ElevenLabs(api_key=config.get("elevenlabs").get("api_key"))
        self.prerecorded = Prerecorded(elevenlabs_inst, self.agent_config.get("fillers"), self.brand)

        self.audio_processor = AudioProcessor(
            elevenlabs_inst,
            self.prerecorded,
            self.agent_config,
            self.memory
        )
        self.llmClient = llmClient

        self.radio_dj_agent = RadioDJAgent(
            config,
            self.memory,
            self.audio_processor,
            self.agent_config,
            self.brand,
            mcp_client=self.mcp_client,
            llmClient=llmClient
        )

        self.broadcast_tool = Queue(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self._played_songs_history: List[str] = []
        self._cooldown_songs_count: int = self.agent_config.get('songCooldown', 4)

    async def run(self) -> None:
        self.logger.info(f"Starting DJ Agent run for brand: {self.brand}")
        self.logger.info(f"Agent name: {self.agent_config.get('name')}")
        self.logger.info(f"Talkativity: {self.talkativity}")

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.connect()

        await self._feed_broadcast()

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")

    async def _feed_broadcast(self) -> None:
        try:
            if self.prerecorded.audio_files and random.random() > self.talkativity:
                await self._handle_prerecorded_broadcast()
            else:
                await self._handle_live_dj_broadcast()
        except Exception as e:
            self.logger.error(f"Error in _feed_broadcast: {e}")
            raise

    async def _handle_prerecorded_broadcast(self) -> None:
        audio_data, message = await self.prerecorded.get_prerecorded_audio()

        songs = self.song_fetch_tool.fetch_songs(self.brand)
        if songs:
            chosen_song = random.choice(songs)
            song_id = chosen_song.get('id')
            sound_fragment = chosen_song.get('soundfragment')
            if self.broadcast_tool.send_to_broadcast(self.brand, song_id, audio_data, f"-{sound_fragment.get('title')}-{sound_fragment.get('artist')}"):
                self.logger.info(f"Broadcasted prerecorded content: {message}")
            else:
                self.logger.warning(f"Failed to broadcast prerecorded content")
        else:
            self.logger.warning(f"No prerecorded audio available: {message}")

    async def _handle_live_dj_broadcast(self) -> None:
        audio_data, song_id, title, artist = await self.radio_dj_agent.create_introduction(
            brand=self.brand
        )

        if audio_data:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_id, audio_data, f"--{title}-{artist}"):
                self.logger.info(f"Broadcasted live DJ intro: {title} by {artist}")
            else:
                self.logger.warning(f"Failed to broadcast live DJ content")
        else:
            self.logger.warning(f"No live DJ audio generated")

    async def cleanup(self):
        if hasattr(self, 'mcp_client') and not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()