import asyncio
import logging
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
from mcp.queue_mcp import QueueMCP
from mcp.server.llm_response import LlmResponse
from mcp.sound_fragment_mcp import SoundFragmentMCP
from util.file_util import debug_log
from util.intro_helper import get_random_ad_intro
from util.prompt_formatter import flatten_data_for_prompt


class DJState(MessagesState):
    events: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    action_type: str
    context: List[str]
    available_ad: List[Dict[str, Any]]
    selected_sound_fragment: Dict[str, Any]
    complimentary_sound_fragment: Dict[str, Any]
    has_complimentary: bool
    introduction_text: str
    audio_data: Optional[bytes]
    title: str
    artist: str
    genres: List[str]
    song_description: str
    listeners: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
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
        self.ai_logger = logging.getLogger('tools.interaction_tools.ai')
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
        self.search_engine = self.agent_config.get("search_engine_type")
        debug_log(f"RadioDJAgent v1 initialized, llm:{self.llm_type}, search engine:{self.search_engine}")

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)
        workflow.add_node("decision", self._decision)
        workflow.add_node("fetch_song", self._fetch_song)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("decision")

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

    async def _decision(self, state: DJState) -> DJState:
        debug_log("Entering _decision")

        if not state["events"]:
            state["action_type"] = "song"
            state["available_ad"] = []
            debug_log(f"No events - defaulting to song")
            return state

        has_ad_event = any(
            event.get("type") == "AD"
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
                state["song_description"] = ad.get('description', '')
                debug_log("AD event detected - setting action to ad")
                return state
            else:
                state["action_type"] = "song"
                state["available_ad"] = []
        else:
            state["action_type"] = "song"
            state["available_ad"] = []
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
                state["song_description"] = song.get('description', '')

                debug_log(f"Has complimentary fragment: {state['has_complimentary']}")

                formatted_events, formatted_history, formatted_listeners, formatted_genres, formatted_messages, formatted_context = flatten_data_for_prompt(
                    events=state["events"],
                    history=state["history"],
                    listeners=state["listeners"],
                    genres=state["genres"],
                    messages=state["messages"],
                    context=state["context"]
                )

                debug_log("ai_dj_name", self.ai_dj_name)
                debug_log("context", formatted_context)
                debug_log("brand", self.brand)
                debug_log("events", formatted_events)
                debug_log("title", state["title"])
                debug_log("artist", state["artist"])
                debug_log("song_description", state["song_description"])
                debug_log("genres", formatted_genres)
                debug_log("history", formatted_history)
                debug_log("listeners", formatted_listeners)
                debug_log("messages", formatted_messages)

                song_prompt = self.agent_config["prompt"].format(
                    ai_dj_name=self.ai_dj_name,
                    context=formatted_context,
                    brand=self.brand,
                    events=formatted_events,
                    title=state["title"],
                    artist=state["artist"],
                    genres=formatted_genres,
                    history=formatted_history,
                    listeners=formatted_listeners,
                    messages=formatted_messages,
                    song_description=state["song_description"]
                )

                messages = [
                    {"role": "system", "content": "Generate plain text"},
                    {"role": "user", "content": song_prompt}
                ]
                tools = [InternetMCP.get_tool_definition(default_engine=self.search_engine)]
                response = await self.llm.ainvoke(messages=messages, tools=tools)

                try:
                    llm_response = LlmResponse.from_response(response, self.llm_type)
                    state["introduction_text"] = llm_response.actual_result
                    debug_log(f"Result: >>>>>>> : {state['introduction_text']}...")
                    debug_log(f"Reasoning: >> : {llm_response.reasoning}")
                    self._reset_memory(state["messages"], state["events"])
                    self.ai_logger.info(f"{self.brand} FINAL_RESULT: {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n")
                except Exception as parse_error:
                    self.logger.error(f"LLM Response parsing failed: {parse_error}")
                    self.logger.error(f"Raw LLM Response: {repr(response)}")
                    self.logger.error(f"Response type: {type(response)}")
                    self.logger.error(f"Response attributes: {dir(response)}")
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
                chosen_ext = "mp3"
                if audio_data and len(audio_data) >= 12 and audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
                    chosen_ext = "wav"
                file_name = f"mixpla_{uuid.uuid4().hex}.{chosen_ext}"
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
                result = False
                max_retries = 2
                for attempt in range(max_retries):
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
                    await asyncio.sleep(2)

                state["broadcast_success"] = result
                if result:
                    state["broadcast_message"] = f"Broadcasted: {state['title']} by {state['artist']}"
                else:
                    state["broadcast_message"] = "Broadcast failed after retries"

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

    async def create_introduction(self, brand: str, memory_data: Dict[str, Any] = None) -> Tuple[
        bool, str, str, str]:
        debug_log(f"create_introduction called for brand: {brand}")
        debug_log(f"memory provided: {memory_data is not None}")
        initial_state = {
            "brand": brand,
            "events": memory_data.get("events", []),
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
            "song_description": "",
            "listeners": memory_data.get("listeners", []),
            "history": memory_data.get("history", []),
            "context": memory_data.get("environment", []),
            "messages": memory_data.get("messages", []),
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

    def _reset_memory(self, messages, events):

        if events:
            for ev in events:
                ev_id = ev.get("id")
                if ev_id:
                    self.memory.reset_event_by_id(ev_id)

        if messages:
            for msg in messages:
                msg_id = msg.get("id")
                if msg_id:
                    self.memory.reset_message_by_id(msg_id)
