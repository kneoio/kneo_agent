import logging
from pathlib import Path
from typing import Optional, Tuple

from elevenlabs.client import ElevenLabs
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from tools.filler_generator import FillerGenerator
from mcp.soundfragment_mcp import SoundfragmentMCP
from tools.audio_processor import AudioProcessor
from tools.song_selector import SongSelector
from tools.introduction_generator import IntroductionGenerator
from tools.dj_state import DJState


class RadioDJAgent:
    """Main Radio DJ Agent orchestrating the workflow"""

    def __init__(self, config, memory: InteractionMemory, language="en",
                 agent_config=None, radio_station_name=None, mcp_client=None):
        self.logger = logging.getLogger(__name__)

        # Initialize LLM
        self.llm = ChatAnthropic(
            model_name=config.get("claude").get("model"),
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        # Initialize components
        self.memory = memory
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.radio_station_name = radio_station_name

        # Initialize specialized components
        self.music_catalog = SoundfragmentMCP(mcp_client)
        self.song_selector = SongSelector(self.llm, self.ai_dj_name)
        self.intro_generator = IntroductionGenerator(self.llm, self.ai_dj_name)

        # Initialize audio processor
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

        # Build workflow graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the workflow graph"""
        workflow = StateGraph(state_schema=DJState)

        # Add nodes
        workflow.add_node("check_prerecorded", self._check_prerecorded)
        workflow.add_node("fetch_songs", self._fetch_songs)
        workflow.add_node("select_song", self._select_song)
        workflow.add_node("generate_intro", self._generate_intro)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("use_prerecorded", self._use_prerecorded)

        # Set entry point
        workflow.set_entry_point("check_prerecorded")

        # Add conditional edges
        workflow.add_conditional_edges(
            "check_prerecorded",
            self._should_use_prerecorded,
            {
                "prerecorded": "use_prerecorded",
                "generate": "fetch_songs"  # Always fetch songs now
            }
        )

        # Add linear flow for song processing
        workflow.add_edge("fetch_songs", "select_song")
        workflow.add_edge("select_song", "generate_intro")
        workflow.add_edge("generate_intro", "create_audio")

        # End nodes
        workflow.add_edge("create_audio", END)
        workflow.add_edge("use_prerecorded", END)

        return workflow.compile()

    async def _check_prerecorded(self, state: DJState) -> DJState:
        """Check if prerecorded audio should be used"""
        state["reason"] = "Checking prerecorded options"
        return state

    def _should_use_prerecorded(self, state: DJState) -> str:
        """Decide between prerecorded and generated content"""
        if self.audio_processor.should_use_prerecorded():
            return "prerecorded"
        return "generate"

    async def _use_prerecorded(self, state: DJState) -> DJState:
        """Use prerecorded audio"""
        audio_data, reason = await self.audio_processor.get_prerecorded_audio()

        state["audio_data"] = audio_data
        state["reason"] = reason
        state["title"] = "Unknown"
        state["artist"] = "Unknown"

        return state

    async def _fetch_songs(self, state: DJState) -> DJState:
        """Fetch songs from music catalog"""
        songs = await self.music_catalog.get_songs(state["brand"])
        state["songs"] = songs

        if not songs:
            state["reason"] = "No songs available from catalog"

        return state

    async def _select_song(self, state: DJState) -> DJState:
        """Select best song from catalog"""
        if not state["songs"]:
            state["selected_song"] = {}
            state["reason"] = "No songs to select from"
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
            return state

        # Get memory context
        memory_data = self.memory.get_all_memory_data()

        # Select song using LLM
        selected_song = await self.song_selector.select_song(
            state["songs"],
            state["brand"],
            memory_data
        )

        state["selected_song"] = selected_song

        # Extract song info
        song_info = selected_song.get('soundfragment', {})
        state["title"] = song_info.get('title', 'Unknown')
        state["artist"] = song_info.get('artist', 'Unknown')

        return state

    async def _generate_intro(self, state: DJState) -> DJState:
        """Generate introduction text"""
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
        """Create final audio from introduction text"""
        audio_data, reason = await self.audio_processor.generate_tts_audio(
            state["introduction_text"],
            state["title"],
            state["artist"]
        )

        state["audio_data"] = audio_data
        state["reason"] = reason

        return state

    async def create_introduction(self, brand: str, agent_config=None) -> Tuple[Optional[bytes], str, str, str]:
        """Main entry point for creating radio introduction"""
        # Reset memory events and messages
        self._reset_memory()

        # Initial state
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
            # Execute workflow
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
        """Reset temporary memory data"""
        memory_data = self.memory.get_all_memory_data()

        # Reset instant messages
        if memory_data.get('messages'):
            self.logger.info("Resetting instant messages")
            self.memory.reset_messages()

        # Reset events
        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])
        if events and event_ids:
            self.logger.info(f"Resetting {len(event_ids)} events")
            for event_id in event_ids:
                self.memory.reset_event_by_id(event_id)
