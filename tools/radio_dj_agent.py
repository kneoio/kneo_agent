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
    events: List[Dict[str, Any]]
    action_type: str
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
        
        # Core workflow nodes
        workflow.add_node("check_events", self._check_events)
        workflow.add_node("llm_decision", self._llm_decision)
        workflow.add_node("fetch_songs", self._fetch_songs)
        workflow.add_node("request_sound_fragment", self._request_sound_fragment)
        workflow.add_node("create_audio", self._create_audio)
        
        workflow.set_entry_point("check_events")
        
        # Main flow
        workflow.add_edge("check_events", "llm_decision")
        
        # Decision branching based on event types
        workflow.add_conditional_edges(
            "llm_decision",
            self._route_action,
            {
                "song": "fetch_songs",
                "ad": "request_sound_fragment"
            }
        )
        
        # Song path (includes birthday with congratulatory intro)
        workflow.add_edge("fetch_songs", "create_audio")
        
        # Ad path
        workflow.add_edge("request_sound_fragment", "create_audio")
        
        # All paths end
        workflow.add_edge("create_audio", END)
        
        return workflow.compile()

    async def _check_events(self, state: DJState) -> DJState:
        """Check for incoming events including birthdays, ads, and broadcast events"""
        events = await self.memory_mcp.get_events(state["brand"])
        state["events"] = events
        state["reason"] = f"Found {len(events)} events to process"
        return state

    async def _llm_decision(self, state: DJState) -> DJState:
        """LLM analyzes events and context to determine action and generate intro/speech"""
        memory_data = self.memory.get_all_memory_data()
        
        # Analyze events to determine action type
        action_type = "song"  # Default
        
        for event in state["events"]:
            event_type = event.get("type", "").lower()
            if "ad" in event_type or "advertisement" in event_type:
                action_type = "ad"
                break
            # Birthday and other events still go to song path but with special intro
        
        # Build context for LLM intro generation
        context_prompt = self.agent_config["prompt"].format(
            ai_dj_name=self.ai_dj_name,
            radio_station_name=self.radio_station_name,
            events=state["events"],
            brand=state["brand"],
            memory_data=memory_data
        )
        
        try:
            response = await self.llm.ainvoke(context_prompt)
            # LLM generates the intro/speech based on events and context
            state["introduction_text"] = response.content
            state["action_type"] = action_type
            state["reason"] = f"LLM generated intro for {action_type} action"
            
        except Exception as e:
            self.logger.error(f"LLM intro generation failed: {e}")
            state["introduction_text"] = "Welcome to our radio show!"
            state["action_type"] = "song"
            state["reason"] = f"LLM intro generation failed: {str(e)}"
            
        return state

    def _route_action(self, state: DJState) -> str:
        """Route to appropriate path based on event analysis"""
        return state["action_type"]



    async def _fetch_songs(self, state: DJState) -> DJState:
        from cnst.play_list_item_type import PlaylistItemType
        songs = await self.sf_mcp.get_songs(state["brand"], types=[PlaylistItemType.SONG.value])
        state["songs"] = songs

        if not songs:
            state["reason"] = "No songs available from catalog"
            state["selected_song"] = {}
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
        else:
            # Let LLM decision handle song selection
            memory_data = self.memory.get_all_memory_data()
            
            # Build context for LLM song selection
            context_prompt = self.agent_config["prompt"].format(
                ai_dj_name=self.ai_dj_name,
                radio_station_name=self.radio_station_name,
                events=state["events"],
                brand=state["brand"],
                memory_data=memory_data,
                songs=songs
            )
            
            try:
                response = await self.llm.ainvoke(context_prompt)
                # Parse response to extract selected song
                # Assuming the LLM returns song selection info
                selected_song = self._parse_song_selection(response.content, songs)
                state["selected_song"] = selected_song
                
                song_info = selected_song.get('soundfragment', {})
                state["title"] = song_info.get('title', 'Unknown')
                state["artist"] = song_info.get('artist', 'Unknown')
                state["reason"] = "LLM selected song"
                
            except Exception as e:
                self.logger.error(f"LLM song selection failed: {e}")
                # Fallback to first song
                state["selected_song"] = songs[0] if songs else {}
                song_info = state["selected_song"].get('soundfragment', {})
                state["title"] = song_info.get('title', 'Unknown')
                state["artist"] = song_info.get('artist', 'Unknown')
                state["reason"] = f"LLM song selection failed, using first song: {str(e)}"

        return state

    def _parse_song_selection(self, llm_response: str, songs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse LLM JSON response to extract selected song by UUID"""
        import json
        import re
        
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^}]*"selected_song_uuid"[^}]*\}', llm_response)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                song_uuid = parsed.get('selected_song_uuid', '')
                
                # Find song by UUID
                for song in songs:
                    if song.get('uuid') == song_uuid or song.get('id') == song_uuid:
                        return song
            
            # Fallback: look for UUID pattern in response
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            uuid_match = re.search(uuid_pattern, llm_response.lower())
            if uuid_match:
                song_uuid = uuid_match.group(0)
                for song in songs:
                    if song.get('uuid') == song_uuid or song.get('id') == song_uuid:
                        return song
            
            # Final fallback: return first song
            return songs[0] if songs else {}
            
        except Exception as e:
            self.logger.error(f"Error parsing song selection: {e}")
            return songs[0] if songs else {}

    async def _request_sound_fragment(self, state: DJState) -> DJState:
        from cnst.play_list_item_type import PlaylistItemType
        ads = await self.sf_mcp.get_songs(state["brand"], types=[PlaylistItemType.ADVERTISEMENT.value])
        
        if ads:
            selected_ad = ads[0]
            state["selected_song"] = selected_ad
            ad_info = selected_ad.get('soundfragment', {})
            state["title"] = ad_info.get('title', 'Advertisement')
            state["artist"] = ad_info.get('artist', 'Sponsor')
            state["reason"] = "Advertisement sound fragment selected"
        else:
            state["selected_song"] = {}
            state["title"] = "Advertisement"
            state["artist"] = "Sponsor"
            state["reason"] = "No advertisement sound fragments available"
        
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
            "events": [],
            "action_type": "",
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
