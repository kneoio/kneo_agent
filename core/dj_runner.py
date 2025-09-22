import logging
import random
from typing import Dict

from elevenlabs import ElevenLabs

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from api.sound_fragment import SoundFragment
from cnst.llm_types import LlmType
from core.prerecorded import Prerecorded
from mcp.mcp_client import MCPClient
from mcp.queue_mcp import QueueMCP
from mcp.sound_fragment_mcp import SoundFragmentMCP
from tools.audio_processor import AudioProcessor
from tools.radio_dj import RadioDJ
from tools.radio_dj_agent import RadioDJAgent


class DJRunner:
    def __init__(self, config: Dict, brand_config: Dict, api_client: BroadcasterAPIClient,
                 mcp_client=None, llm_client=None, llm_type=LlmType.CLAUDE):
        self.logger = logging.getLogger(__name__)
        self.brand_config = brand_config
        self.brand = brand_config.get('radioStationName')
        self.agent_config = brand_config.get('agent', {})
        self.talkativity = self.agent_config.get('talkativity', 0.3)
        self.mcp_client = mcp_client if mcp_client else MCPClient(config, True)
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
        #self.radio_dj_agent = RadioDJAgent(
        #    config,
        #    self.memory,
        #    self.audio_processor,
        #    self.agent_config,
        #    self.brand,
        #    mcp_client=self.mcp_client,
        #    llm_client=llm_client,
        #    llm_type=llm_type
        #)
        self.radio_dj = RadioDJ(
            config,
            self.memory,
            self.audio_processor,
            self.agent_config,
            self.brand,
            mcp_client=self.mcp_client,
            llm_client=llm_client,
            llm_type=llm_type
        )
        self.sound_fragments_mcp = SoundFragmentMCP(self.mcp_client)
        self.queue_mcp = QueueMCP(self.mcp_client)

    async def run(self) -> None:
        self.logger.info(
            f"Starting DJ Agent run for: {self.brand}, DJ: {self.agent_config.get('name')}, Talkativity: {self.talkativity}")

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.connect()

        await self._feed_broadcast()

        if not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()

        self.logger.info(f"DJ Agent run completed for brand: {self.brand}")

    async def _feed_broadcast(self) -> None:
        try:
            if self.prerecorded.audio_files and random.random() < self.talkativity:
                await self._handle_live_dj_broadcast()
            else:
                await self._handle_prerecorded_broadcast()
        except Exception as e:
            self.logger.error(f"Error in _feed_broadcast: {e}")
            raise

    async def _handle_prerecorded_broadcast(self) -> None:
        temp_file_path, message = await self.prerecorded.get_prerecorded_file_path()

        if not temp_file_path:
            self.logger.warning(f"No prerecorded audio available: {message}")
            return

        song_list = await self.sound_fragments_mcp.get_brand_sound_fragment(self.brand)
        if not song_list:
            self.logger.warning("No song available for prerecorded broadcast")
            return

        song = song_list[0]

        try:
            result = await self.queue_mcp.add_to_queue_f_s(
                brand_name=self.brand,
                sound_fragment_uuid=song.get('id'),
                file_path=temp_file_path,
                priority=5
            )
            success = result

            if success:
                self.logger.info(f" >>>> Broadcasted: {message}")
            else:
                self.logger.warning(f"Failed to broadcast prerecorded content: {result}")

        except Exception as e:
            self.logger.error(f"Error in prerecorded broadcast: {e}")


    async def _handle_live_dj_broadcast(self) -> None:
        memory_data = self.memory.get_all_memory_data()

        broadcast_success, song_id, title, artist, broadcast_message = await self.radio_dj.run(
            brand=self.brand,
            memory_data=memory_data
        )

        if not broadcast_success:
            self.logger.info("Switching to prerecorded filler — no live DJ intro available")
            await self._handle_prerecorded_broadcast()
        else:
            self.logger.info(f"Successfully broadcasted live DJ intro: {title} by {artist}")

    async def cleanup(self):
        if hasattr(self, 'mcp_client') and not hasattr(self, '_external_mcp_client'):
            await self.mcp_client.disconnect()