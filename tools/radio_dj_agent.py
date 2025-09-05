import json
import logging
import re
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple

from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from api.queue import Queue
from cnst.llm_types import LlmType
from cnst.play_list_item_type import PlaylistItemType
from mcp.external.internet_mcp import InternetMCP
from mcp.server.llm_response import LlmResponse
from mcp.sound_fragment_mcp import SoundFragmentMCP
from mcp.queue_mcp import QueueMCP
from util.file_util import debug_log
from util.intro_helper import get_random_ad_intro


class DJState(MessagesState):
    events: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    action_type: str
    context: str
    available_ad: List[Dict[str, Any]]
    selected_sound_fragment: Dict[str, Any]
    complimentary_sound_fragment: Dict[str, Any]
    has_complimentary: bool
    introduction_text: str
    audio_data: Optional[bytes]
    title: str
    artist: str
    genres: List[str]
    listeners: List[Dict[str, Any]]
    instant_message: List[Dict[str, Any]]
    http_memory_data: Dict[str, Any]
    file_path: Optional[str]
    broadcast_success: bool
    broadcast_message: str


def _route_action(state: DJState) -> str:
    return state["action_type"]


def _route_song_fetch(state: DJState) -> str:
    if not state["selected_sound_fragment"]:
        return "end"
    return "create_audio"

class RadioDJAgent:

    def __init__(self, config, memory: InteractionMemory, audio_processor, agent_config=None, brand=None,
                 mcp_client=None, debug=False, llm_client=None, llm_type=LlmType.CLAUDE):
        self.debug = debug
        self.llm_type = llm_type
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

        self.llm = llm_client
        self.queue = Queue(config)
        self.memory = memory
        self.audio_processor = audio_processor
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.brand = brand
        self.sound_fragments_mcp = SoundFragmentMCP(mcp_client)
        self.queue_mcp = QueueMCP(mcp_client)
        self.graph = self._build_graph()
        debug_log(f"RadioDJAgent initialized, llm:{self.llm_type}")

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)
        workflow.add_node("check_events", self._check_events)
        workflow.add_node("decision", self._decision)
        workflow.add_node("fetch_song", self._fetch_song)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("check_events")

        workflow.add_edge("check_events", "decision")

        workflow.add_conditional_edges(
            "decision",
            _route_action,
            {
                "song": "fetch_song",
                "ad": "create_audio"
            }
        )

        workflow.add_conditional_edges(
            "fetch_song",
            _route_song_fetch,
            {
                "create_audio": "create_audio",
                "end": END
            }
        )

        workflow.add_edge("create_audio", "broadcast_audio")
        workflow.add_edge("broadcast_audio", END)

        debug_log("Graph workflow built")
        return workflow.compile()

    async def _check_events(self, state: DJState) -> DJState:
        debug_log("Entering _check_events")

        try:
            http_memory_data = state.get("http_memory_data", {})
            state["events"] = http_memory_data.get("events", [])
        except Exception as e:
            self.logger.error(f"Error checking events: {e}", exc_info=self.debug)
            state["events"] = []

        return state

    async def _decision(self, state: DJState) -> DJState:
        debug_log("Entering _decision")

        memory_data = self.memory.get_all_memory_data()
        environment = memory_data.get("environment", [])
        if isinstance(environment, list) and environment:
            state["context"] = environment[0]
        elif isinstance(environment, str):
            state["context"] = environment
        else:
            state["context"] = ""

        if not state["events"]:
            state["action_type"] = "song"
            state["available_ad"] = []
            http_memory_data = state.get("http_memory_data", {})
            state["history"] = http_memory_data.get("history", [])
            state["listeners"] = http_memory_data.get("listeners", [])
            debug_log(f"No events - defaulting to song")
            return state

        has_ad_event = any(
            event.get("content", {}).get("type") == "AD"
            for event in state["events"]
            if isinstance(event, dict)
        )

        if has_ad_event:
            ad_list = await self.sound_fragments_mcp.get_brand_sound_fragment(
                brand=self.brand,
                fragment_type=PlaylistItemType.ADVERTISEMENT.value)

            if ad_list:
                state["available_ad"] = ad_list
                state["action_type"] = "ad"
                ad = ad_list[0]
                state["introduction_text"] = get_random_ad_intro()
                state["selected_sound_fragment"] = ad
                state["title"] = ad.get('title', 'Advertisement')
                state["artist"] = ad.get('artist', 'Sponsor')
                debug_log("AD event detected - setting action to ad")
                return state
            else:
                state["action_type"] = "song"
                state["available_ad"] = []
        else:
            ad_list = await self.sound_fragments_mcp.get_brand_sound_fragment(
                brand=self.brand,
                fragment_type=PlaylistItemType.ADVERTISEMENT.value)

            if not ad_list:
                state["action_type"] = "song"
                state["available_ad"] = []
            else:
                state["available_ad"] = ad_list
                ad = ad_list[0] if ad_list else None
                decision_prompt = self.agent_config["decision_prompt"].format(
                    ai_dj_name=self.ai_dj_name,
                    context=state["context"],
                    brand=self.brand,
                    events=state["events"],
                    ad=ad.get("id") if ad else None
                )

                try:
                    decision_prompt = [
                        {"role": "system",
                         "content": "Output JSON only: - Ad: {\"action\": \"ad\", \"introduction_text\": \"here is something from our sponsors\"}"},
                        {"role": "user", "content": decision_prompt}
                    ]
                    response = await self.llm.ainvoke(decision_prompt)
                    debug_log(f"LLM response received: {response.content[:200]}...")
                    parsed_response = self._parse_llm_response(response.content)

                    state["action_type"] = parsed_response.get("action", "song")
                    debug_log("Action type determined", {"action_type": state["action_type"]})

                    if state["action_type"] == "ad":
                        state["introduction_text"] = parsed_response.get("introduction_text", get_random_ad_intro())
                        state["selected_sound_fragment"] = ad
                        state["title"] = ad.get('title', 'Advertisement')
                        state["artist"] = ad.get('artist', 'Sponsor')

                except Exception as e:
                    self.logger.error(f"Decision failed: {e}", exc_info=self.debug)
                    state["action_type"] = "song"
                    self.logger.warning(f"Fallback to default: action=song")

        if state["action_type"] != "ad":
            http_memory_data = state.get("http_memory_data", {})
            state["history"] = http_memory_data.get("history", [])
            state["listeners"] = http_memory_data.get("listeners", [])

            debug_log(f"Retrieved conversation history from HTTP: {len(state['history'])} items")
            debug_log(f"Retrieved listeners from HTTP: {len(state['listeners'])} items")

        return state

    async def _fetch_song(self, state: DJState) -> DJState:
        debug_log("Entering _fetch_song")

        try:
            song_list = await self.sound_fragments_mcp.get_brand_sound_fragment(self.brand)
            if song_list:
                if len(song_list) > 1:
                    state["selected_sound_fragment"] = song_list[1]
                    state["complimentary_sound_fragment"] = song_list[0]
                    state["has_complimentary"] = True
                else:
                    state["selected_sound_fragment"] = song_list[0]
                    state["complimentary_sound_fragment"] = {}
                    state["has_complimentary"] = False

                song = state["selected_sound_fragment"]
                state["title"] = song.get('title')
                state["artist"] = song.get('artist')
                state["genres"] = song.get('genres', [])

                debug_log("state['title']", state["title"])
                debug_log("state['artist']", state["artist"])
                debug_log("state['genres']", state["genres"])
                debug_log("self.ai_dj_name", self.ai_dj_name)
                debug_log("state['context']", state["context"])
                debug_log("state['events']", state["events"])
                debug_log("state['listeners']", state["listeners"])
                debug_log(f"Has complimentary fragment: {state['has_complimentary']}")

                song_prompt = self.agent_config["prompt"].format(
                    ai_dj_name=self.ai_dj_name,
                    context=state["context"],
                    brand=self.brand,
                    events=state["events"],
                    title=state["title"],
                    artist=state["artist"],
                    genres=state["genres"],
                    history=state["history"],
                    listeners=state["listeners"],
                    instant_message=state["instant_message"]
                )

                messages = [
                    {"role": "system", "content": "Generate plain text"},
                    {"role": "user", "content": song_prompt}
                ]
                tools = [InternetMCP.get_tool_definition()]
                response = await self.llm.ainvoke(messages=messages, tools=tools)

                try:
                    llm_response = LlmResponse.from_response(response, self.llm_type)
                    state["introduction_text"] = llm_response.actual_result
                    debug_log(f"Result: >>>> : {state['introduction_text']}...")
                except Exception as parse_error:
                    self.logger.error(f"LLM Response parsing failed: {parse_error}")
                    self.logger.error(f"Raw LLM Response: {repr(response)}")
                    self.logger.error(f"Response content: {getattr(response, 'content', 'NO CONTENT')}")
                    self.logger.error(f"Response type: {type(response)}")
                    self.logger.error(f"Response attributes: {dir(response)}")

                    # Fallback to empty intro
                    state["introduction_text"] = ""

            else:
                debug_log("No song to broadcast.")
                state["selected_sound_fragment"] = {}
                state["complimentary_sound_fragment"] = {}
                state["has_complimentary"] = False
                state["introduction_text"] = ""

        except Exception as e:
            self.logger.error(f"Error in fetch_song: {e}")
            state["selected_sound_fragment"] = {}
            state["complimentary_sound_fragment"] = {}
            state["has_complimentary"] = False
            state["introduction_text"] = ""

        return state

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        try:
            json_match = re.search(r'\{[^}]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                self.logger.error(f"Parsing LLM response issue: {response}")
                return {}
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {}

    async def _create_audio(self, state: DJState) -> DJState:
        debug_log("Entering _create_audio")

        try:
            audio_data, reason = await self.audio_processor.generate_tts_audio(
                state["introduction_text"],
                state["title"],
                state["artist"]
            )

            state["audio_data"] = audio_data

            if audio_data:
                target_dir = "/home/kneobroadcaster/merged"
                os.makedirs(target_dir, exist_ok=True)
                file_name = f"mixpla_{uuid.uuid4().hex}.mp3"
                full_path = os.path.join(target_dir, file_name)
                with open(full_path, "wb") as f:
                    f.write(audio_data)
                state["file_path"] = full_path
                debug_log(f"Audio saved to: {full_path}")

        except Exception as e:
            self.logger.error(f"Error creating audio: {e}", exc_info=self.debug)
            state["file_path"] = None

        return state

    async def _broadcast_audio(self, state: DJState) -> DJState:
        debug_log("Entering _broadcast_audio")

        try:
            if state.get("file_path") and state.get("selected_sound_fragment"):
                while True:
                    if state["has_complimentary"]:
                        result = await self.queue_mcp.add_to_queue_s_i_s(
                            brand_name=self.brand,
                            fragment_uuid_1=state["complimentary_sound_fragment"].get("id"),
                            fragment_uuid_2=state["selected_sound_fragment"].get("id"),
                            file_path=state["file_path"],
                            priority=10
                        )
                    else:
                        result = await self.queue_mcp.add_to_queue_i_s(
                            brand_name=self.brand,
                            sound_fragment_uuid=state["selected_sound_fragment"].get("id"),
                            file_path=state["file_path"],
                            priority=10
                        )
                    if result:
                        break

                state["broadcast_success"] = result
                state["broadcast_message"] = f"Broadcasted: {state['title']} by {state['artist']}"

                debug_log(f"Broadcasting result: {state['broadcast_success']}")

            else:
                state["broadcast_success"] = False
                state["broadcast_message"] = "No audio or sound fragment to broadcast"
                debug_log("Broadcasting skipped: missing audio or sound fragment")

        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}", exc_info=self.debug)
            state["broadcast_success"] = False
            state["broadcast_message"] = f"Broadcast failed: {str(e)}"

        return state

    async def create_introduction(self, brand: str, http_memory_data: Dict[str, Any] = None) -> Tuple[
        bool, str, str, str]:
        debug_log(f"create_introduction called for brand: {brand}")
        debug_log(f"http_memory_data provided: {http_memory_data is not None}")
        self._reset_memory()

        initial_state = {
            "messages": [],
            "brand": brand,
            "events": [],
            "action_type": "",
            "available_ad": [],
            "selected_sound_fragment": {},
            "complimentary_sound_fragment": {},
            "has_complimentary": False,
            "introduction_text": "",
            "audio_data": None,
            "title": "Unknown",
            "artist": "Unknown",
            "genres": [],
            "listeners": [],
            "history": [],
            "instant_message": [],
            "http_memory_data": http_memory_data or {},
            "file_path": None,
            "broadcast_success": False,
            "broadcast_message": ""
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            return (
                result["broadcast_success"],
                result["selected_sound_fragment"].get("id", "Unknown"),
                result["title"],
                result["artist"]
            )
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}", exc_info=self.debug)
            return False, "Unknown", "Unknown", "Unknown"

    def _reset_memory(self):
        memory_data = self.memory.get_all_memory_data()
        if memory_data.get('messages'):
            self.memory.reset_messages()
        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])
        if events and event_ids:
            for event_id in event_ids:
                self.memory.reset_event_by_id(event_id)
