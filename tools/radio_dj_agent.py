import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from elevenlabs.client import ElevenLabs
from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from mcp.memory_mcp import MemoryMCP
from mcp.sound_fragment_mcp import SoundFragmentMCP
from tools.audio_processor import AudioProcessor
from tools.filler_generator import FillerGenerator
from tools.introduction_generator import IntroductionGenerator
from tools.song_selector import SongSelector


class DJState(MessagesState):
    brand: str
    songs: List[Dict[str, Any]]
    selected_song: Dict[str, Any]
    introduction_text: str
    audio_data: Optional[bytes]
    reason: str
    title: str
    artist: str


class RadioDJAgent:

    def __init__(self, config, memory: InteractionMemory, agent_config=None, radio_station_name=None, mcp_client=None):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatAnthropic(
            model_name=config.get("claude").get("model"),
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.memory = memory
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.radio_station_name = radio_station_name
        self.sf_mcp = SoundFragmentMCP(mcp_client)
        self.memory_mcp = MemoryMCP(mcp_client)
        self.song_selector = SongSelector(self.llm, self.ai_dj_name)
        self.intro_generator = IntroductionGenerator(self.llm, self.ai_dj_name)

        metadata_folder = Path("metadata") / self.radio_station_name
        filler_generator = FillerGenerator(
            ElevenLabs(api_key=config.get("elevenlabs").get("api_key")),
            metadata_folder
        )
        self.audio_processor = AudioProcessor(
            ElevenLabs(api_key=config.get("elevenlabs").get("api_key")),
            filler_generator,
            self.agent_config,
            memory
        )

        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)
        workflow.add_node("check_prerecorded", self._check_prerecorded)
        workflow.add_node("fetch_songs", self._fetch_songs)
        workflow.add_node("select_song", self._select_song)
        workflow.add_node("generate_intro", self._generate_intro)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("use_prerecorded", self._use_prerecorded)
        workflow.set_entry_point("check_prerecorded")

        workflow.add_conditional_edges(
            "check_prerecorded",
            self._should_use_prerecorded,
            {
                "prerecorded": "use_prerecorded",
                "generate": "fetch_songs"
            }
        )

        workflow.add_edge("fetch_songs", "select_song")
        workflow.add_edge("select_song", "generate_intro")
        workflow.add_edge("generate_intro", "create_audio")

        workflow.add_edge("create_audio", END)
        workflow.add_edge("use_prerecorded", END)

        return workflow.compile()

    async def _check_prerecorded(self, state: DJState) -> DJState:
        """Check if prerecorded audio should be used"""
        state["reason"] = "Checking prerecorded options"
        return state

    def _should_use_prerecorded(self) -> str:
        if self.audio_processor.should_use_prerecorded():
            return "prerecorded"
        return "generate"

    async def _use_prerecorded(self, state: DJState) -> DJState:
        audio_data, reason = await self.audio_processor.get_prerecorded_audio()

        state["audio_data"] = audio_data
        state["reason"] = reason
        state["title"] = "Unknown"
        state["artist"] = "Unknown"

        return state

    async def _fetch_songs(self, state: DJState) -> DJState:
        songs = await self.sf_mcp.get_songs(state["brand"])
        state["songs"] = songs

        if not songs:
            state["reason"] = "No songs available from catalog"

        return state

    async def _select_song(self, state: DJState) -> DJState:
        if not state["songs"]:
            state["selected_song"] = {}
            state["reason"] = "No songs to select from"
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
            return state

        memory_data = self.memory.get_all_memory_data()

        selected_song = await self.song_selector.select_song(
            state["songs"],
            state["brand"],
            memory_data
        )

        state["selected_song"] = selected_song
        song_info = selected_song.get('soundfragment', {})
        state["title"] = song_info.get('title', 'Unknown')
        state["artist"] = song_info.get('artist', 'Unknown')

        return state

    async def _generate_intro(self, state: DJState) -> DJState:
        memory_data = self.memory.get_all_memory_data()

        intro_text = await self.intro_generator.generate_intro(
            state["title"],
            state["artist"],
            state["brand"],
            memory_data
        )

        state["introduction_text"] = intro_text
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        audio_data, reason = await self.audio_processor.generate_tts_audio(
            state["introduction_text"],
            state["title"],
            state["artist"]
        )

        state["audio_data"] = audio_data
        state["reason"] = reason

        return state

    async def create_introduction(self, brand: str) -> Tuple[Optional[bytes], str, str, str]:
        self._reset_memory()

        initial_state = {
            "messages": [],
            "brand": brand,
            "songs": [],
            "selected_song": {},
            "introduction_text": "",
            "audio_data": None,
            "reason": "",
            "title": "Unknown",
            "artist": "Unknown"
        }

        try:
            result = await self.graph.ainvoke(initial_state)

            return (
                result["audio_data"],
                result["reason"],
                result["title"],
                result["artist"]
            )

        except Exception as e:
            reason = f"Workflow execution failed: {str(e)}"
            self.logger.exception(reason)
            return None, reason, "Unknown", "Unknown"

    def _reset_memory(self):
        memory_data = self.memory.get_all_memory_data()

        if memory_data.get('messages'):
            self.logger.info("Resetting instant messages")
            self.memory.reset_messages()

        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])
        if events and event_ids:
            self.logger.info(f"Resetting {len(event_ids)} events")
            for event_id in event_ids:
                self.memory.reset_event_by_id(event_id)
