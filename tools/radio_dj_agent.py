import logging
import json
import queue
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from elevenlabs.client import ElevenLabs
from langchain_anthropic import ChatAnthropic
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from cnst.play_list_item_type import PlaylistItemType
from mcp.memory_mcp import MemoryMCP
from mcp.sound_fragment_mcp import SoundFragmentMCP
from tools.audio_processor import AudioProcessor
from tools.filler_generator import FillerGenerator
from tools.queue_tool import QueueTool


class DJState(MessagesState):
    brand: str
    events: List[Dict[str, Any]]
    action_type: str
    mood: str
    context: str
    available_ads: List[Dict[str, Any]]
    selected_song: Dict[str, Any]
    introduction_text: str
    audio_data: Optional[bytes]
    reason: str
    title: str
    artist: str


class RadioDJAgent:

    def __init__(self, config, memory: InteractionMemory, agent_config=None, radio_station_name=None, mcp_client=None,
                 debug=True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

        self.llm = ChatAnthropic(
            model_name=config.get("claude").get("model"),
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.queue = QueueTool(config)
        self.memory = memory
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.context = self.agent_config.get("context")
        self.radio_station_name = radio_station_name
        self.sf_mcp = SoundFragmentMCP(mcp_client)
        self.memory_mcp = MemoryMCP(mcp_client)

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

        if self.debug:
            self._load_external_prompts()

        self.graph = self._build_graph()
        self._debug_log("RadioDJAgent initialized")

    def _load_external_prompts(self):
        try:
            decision_prompt_path = Path("prompts/decision_prompt.json")
            if decision_prompt_path.exists():
                with open(decision_prompt_path, 'r', encoding='utf-8') as f:
                    decision_data = json.load(f)
                    self.agent_config["decision_prompt"] = decision_data.get("prompt", self.agent_config.get("decision_prompt", ""))
                self._debug_log(f"Loaded decision_prompt from {decision_prompt_path}")
            else:
                self._debug_log(f"Decision prompt file not found: {decision_prompt_path}")

            song_prompt_path = Path("prompts/song_prompt.json")
            if song_prompt_path.exists():
                with open(song_prompt_path, 'r', encoding='utf-8') as f:
                    song_data = json.load(f)
                    self.agent_config["song_prompt"] = song_data.get("prompt", self.agent_config.get("song_prompt", ""))
                self._debug_log(f"Loaded song_prompt from {song_prompt_path}")
            else:
                self._debug_log(f"Song prompt file not found: {song_prompt_path}")

        except Exception as e:
            self.logger.error(f"Error loading external prompts: {e}", exc_info=True)
            self._debug_log(f"Failed to load external prompts, using defaults")

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)
        workflow.add_node("check_events", self._check_events)
        workflow.add_node("decision", self._decision)
        workflow.add_node("fetch_song", self._fetch_song)
        workflow.add_node("create_audio", self._create_audio)
        workflow.set_entry_point("check_events")
        workflow.add_edge("check_events", "decision")

        workflow.add_conditional_edges(
            "decision",
            self._route_action,
            {
                "song": "fetch_song",
                "ad": "create_audio"
            }
        )

        workflow.add_edge("fetch_song", "create_audio")
        workflow.add_edge("create_audio", END)

        self._debug_log("Graph workflow built")
        return workflow.compile()

    async def _check_events(self, state: DJState) -> DJState:
        self._debug_log("Entering _check_events", {"brand": state["brand"]})

        try:
            events = await self.memory_mcp.get_events(state["brand"])
            state["events"] = events
            state["reason"] = f"Found {len(events)} events to process"
            self._debug_log("Events retrieved", {"count": len(events), "events": events})
        except Exception as e:
            self.logger.error(f"Error checking events: {e}", exc_info=self.debug)
            state["events"] = []
            state["reason"] = f"Error checking events: {str(e)}"

        return state

    async def _fetch_ads(self, state: DJState) -> DJState:
        self._debug_log("Entering _fetch_ads")

        try:
            ads = await self.sf_mcp.get_songs(state["brand"], types=PlaylistItemType.ADVERTISEMENT.value)
            state["available_ads"] = ads
            self._debug_log("Ads fetched", {"count": len(ads)})
        except Exception as e:
            self.logger.error(f"Error fetching ads: {e}", exc_info=self.debug)
            state["available_ads"] = []

        return state

    async def _decision(self, state: DJState) -> DJState:
        self._debug_log("Entering _decision")

        try:
            ads = await self.sf_mcp.get_songs(state["brand"], types=[PlaylistItemType.ADVERTISEMENT.value])
            state["available_ads"] = ads
            self._debug_log("Ads fetched", {"count": len(ads)})
        except Exception as e:
            self.logger.error(f"Error fetching ads: {e}", exc_info=self.debug)
            state["available_ads"] = []

        memory_data = self.memory.get_all_memory_data()

        decision_prompt = self.agent_config["decision_prompt"].format(
            ai_dj_name=self.ai_dj_name,
            context=self.context,
            radio_station_name=self.radio_station_name,
            events=state["events"],
            brand=state["brand"],
            memory_data=memory_data,
            ads=state["available_ads"]
        )

        try:
            response = await self.llm.ainvoke(decision_prompt)
            parsed_response = self._parse_llm_response(response.content)

            state["action_type"] = parsed_response.get("action", "song")

            if state["action_type"] == "ad":
                state["introduction_text"] = parsed_response.get("introduction_text", "Time for advertisement")
                selected_uuid = parsed_response.get("selected_song_uuid", "")
                selected_ad = self._find_item_by_uuid(state["available_ads"], selected_uuid)
                state["selected_song"] = selected_ad

                ad_info = selected_ad.get('soundfragment', {})
                state["title"] = ad_info.get('title', 'Advertisement')
                state["artist"] = ad_info.get('artist', 'Sponsor')
            else:
                state["mood"] = parsed_response.get("mood", "upbeat")

            state["reason"] = f"Decision made: {state['action_type']}"

        except Exception as e:
            self.logger.error(f"Decision failed: {e}", exc_info=self.debug)
            state["action_type"] = "song"
            state["mood"] = "upbeat"
            state["reason"] = f"Decision failed: {str(e)}"

        return state

    def _route_action(self, state: DJState) -> str:
        return state["action_type"]

    async def _fetch_song(self, state: DJState) -> DJState:
        self._debug_log("Entering _fetch_song")

        try:
            song = await self.sf_mcp.get_song_by_mood(state["brand"], state["mood"])
            if song:
                state["selected_song"] = song
                song_info = song.get('soundfragment', {})
                state["title"] = song_info.get('title', 'Unknown')
                state["artist"] = song_info.get('artist', 'Unknown')

                memory_data = self.memory.get_all_memory_data()
                song_prompt = self.agent_config["song_prompt"].format(
                    ai_dj_name=self.ai_dj_name,
                    context=self.context,
                    radio_station_name=self.radio_station_name,
                    events=state["events"],
                    brand=state["brand"],
                    memory_data=memory_data,
                    song=song,
                    mood=state["mood"]
                )

                response = await self.llm.ainvoke(song_prompt)
                parsed_response = self._parse_llm_response(response.content)
                state["introduction_text"] = parsed_response.get("introduction_text", "Here's a great song")
                #state["selected_song"] = song_info.get("id")
                state["reason"] = f"Song fetched and intro generated for mood: {state['mood']}"
            else:
                state["selected_song"] = {}
                state["title"] = "Unknown"
                state["artist"] = "Unknown"
                state["introduction_text"] = "Here's some music for you"
                state["reason"] = f"No song found for mood: {state['mood']}"

            self._debug_log("Song processed", {"mood": state["mood"], "title": state["title"]})
        except Exception as e:
            self.logger.error(f"Error in fetch_song: {e}", exc_info=self.debug)
            state["selected_song"] = {}
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
            state["introduction_text"] = "Here's some music for you"
            state["reason"] = f"Error in fetch_song: {str(e)}"

        return state

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        try:
            json_match = re.search(r'\{[^}]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            return {}
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {}

    def _find_item_by_uuid(self, items: List[Dict[str, Any]], uuid: str) -> Dict[str, Any]:
        for item in items:
            if item.get('uuid') == uuid or item.get('id') == uuid:
                return item
        return items[0] if items else {}

    async def _create_audio(self, state: DJState) -> DJState:
        self._debug_log("Entering _create_audio")

        try:
            audio_data, reason = await self.audio_processor.generate_tts_audio(
                state["introduction_text"],
                state["title"],
                state["artist"]
            )

            state["audio_data"] = audio_data
            state["reason"] = reason

        except Exception as e:
            self.logger.error(f"Error creating audio: {e}", exc_info=self.debug)
            state["reason"] = f"Error creating audio: {str(e)}"

        return state

    async def create_introduction(self, brand: str) -> Tuple[Optional[bytes], str, str, str]:
        self._reset_memory()

        initial_state = {
            "messages": [],
            "brand": brand,
            "events": [],
            "action_type": "",
            "mood": "",
            "available_ads": [],
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
                result["selected_song"].get("id"),
                result["title"],
                result["artist"]
            )
        except Exception as e:
            reason = f"Workflow execution failed: {str(e)}"
            self.logger.error(reason, exc_info=self.debug)
            return None, reason, "Unknown", "Unknown"

    def _reset_memory(self):
        memory_data = self.memory.get_all_memory_data()
        if memory_data.get('messages'):
            self.memory.reset_messages()
        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])
        if events and event_ids:
            for event_id in event_ids:
                self.memory.reset_event_by_id(event_id)

    def _debug_log(self, message: str, data: Any = None):
        if self.debug:
            if data is not None:
                print(f"[DEBUG] {message}: {data}")
            else:
                print(f"[DEBUG] {message}")

    def enable_debug(self):
        self.debug = True
        self.logger.setLevel(logging.DEBUG)

    def disable_debug(self):
        self.debug = False
        self.logger.setLevel(logging.INFO)