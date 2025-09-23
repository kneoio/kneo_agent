import logging
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple

from langgraph.graph import MessagesState, StateGraph, END

from api.interaction_memory import InteractionMemory
from api.queue import Queue
from cnst.llm_types import LlmType
from cnst.play_list_item_type import PlaylistItemType
from mcp.external.internet_mcp import InternetMCP
from mcp.queue_mcp import QueueMCP
from mcp.server.llm_response import LlmResponse
from mcp.sound_fragment_mcp import SoundFragmentMCP
from util.file_util import debug_log


class DJState(MessagesState):
    events: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    context: List[str]
    selected_sound_fragment: Dict[str, Any]
    complimentary_sound_fragment: Dict[str, Any]
    has_complimentary: bool
    introduction_text: str
    draft_text: str
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
    __end__: bool


class RadioDJ:

    def __init__(self, config, memory: InteractionMemory, audio_processor, agent_config=None,
                 brand=None, mcp_client=None, debug=False, llm_client=None, llm_type=LlmType.CLAUDE):
        self.debug = debug
        self.llm_type = llm_type
        self.logger = logging.getLogger(__name__)
        self.ai_logger = logging.getLogger("tools.interaction_tools.ai")

        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(handler)

        self.llm = llm_client
        self.queue = Queue(config)
        self.memory = memory
        self.audio_processor = audio_processor
        self.agent_config = agent_config
        self.search_engine = self.agent_config.get("search_engine_type")
        self.ai_dj_name = self.agent_config.get("name")
        self.brand = brand
        self.sound_fragments_mcp = SoundFragmentMCP(mcp_client)
        self.queue_mcp = QueueMCP(mcp_client)
        self.graph = self._build_graph()
        debug_log(f"RadioDJ v2 initialized with llm={self.llm_type}")

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)

        workflow.add_node("build_messages", self._build_messages)
        workflow.add_node("build_events", self._build_events)
        workflow.add_node("fetch_song_fragment", self._fetch_song_fragment)
        workflow.add_node("build_song_intro", self._build_song_intro)
        workflow.add_node("build_ad_intro", self._build_ad_intro)
        workflow.add_node("combine_draft", self._combine_draft)
        workflow.add_node("embellish", self._embellish)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("build_messages")
        workflow.add_edge("build_messages", "build_events")

        # After events, decide if AD or SONG
        workflow.add_conditional_edges(
            "build_events",
            lambda state: "build_ad_intro"
            if any(ev.get("type") == "AD" for ev in state["events"])
            else "fetch_song_fragment",
            {"build_ad_intro": "build_ad_intro", "fetch_song_fragment": "fetch_song_fragment"},
        )

        # AD branch: short-circuit if no ad fragment
        workflow.add_conditional_edges(
            "build_ad_intro",
            lambda state: "end" if state.get("__end__") else "combine_draft",
            {"end": END, "combine_draft": "combine_draft"},
        )

        # SONG branch: short-circuit if no song fragment
        workflow.add_conditional_edges(
            "fetch_song_fragment",
            lambda state: "end" if state.get("__end__") else "build_song_intro",
            {"end": END, "build_song_intro": "build_song_intro"},
        )

        workflow.add_edge("build_song_intro", "combine_draft")
        workflow.add_edge("combine_draft", "embellish")
        workflow.add_edge("embellish", "create_audio")
        workflow.add_edge("create_audio", "broadcast_audio")
        workflow.add_edge("broadcast_audio", END)

        debug_log("Graph workflow built (ads vs songs, with fetch_song_fragment + short-circuit exits)")
        return workflow.compile()

    async def _build_ad_intro(self, state: DJState) -> DJState:
        ad_list = await self.sound_fragments_mcp.get_brand_sound_fragment(
            brand=self.brand,
            fragment_type=PlaylistItemType.ADVERTISEMENT.value
        )
        if ad_list:
            ad = ad_list[0]
            state["selected_sound_fragment"] = ad
            state["title"] = ad.get("title", "Advertisement")
            state["artist"] = ad.get("artist", "Sponsor")
            state["song_description"] = ad.get("description", "")
            state["draft_text"] += f"\nAdvertisement: Break — \"{state['title']}\" by {state['artist']}"
        else:
            self.logger.warning("No advertisement fragment available — skipping ad broadcast")
            state["broadcast_success"] = False
            state["broadcast_message"] = "Skipped — no advertisement fragment"
            state["__end__"] = True
        self._reset_event(state["events"])
        return state

    @staticmethod
    async def _build_messages(state: DJState) -> DJState:
        if state["messages"]:
            msgs = [
                f"Message(For Listeners): {msg.get('from')}: {msg.get('content')}"
                for msg in state["messages"]
            ]
            state["draft_text"] = "\n".join(msgs)
        else:
            state["draft_text"] = ""
        return state

    @staticmethod
    async def _build_events(state: DJState) -> DJState:
        if state["events"]:
            evs = [
                f"Event ({ev.get('type')}): {ev.get('description', '')}"
                for ev in state["events"]
            ]
            state["draft_text"] += "\n" + "\n".join(evs)
        return state

    async def _fetch_song_fragment(self, state: DJState) -> DJState:
        song_list = await self.sound_fragments_mcp.get_brand_sound_fragment(self.brand)

        if song_list:
            if len(song_list) > 1:
                state["selected_sound_fragment"] = song_list[1]
                state["complimentary_sound_fragment"] = song_list[0]
                state["has_complimentary"] = True
                first_song_in_mix = state["complimentary_sound_fragment"]
                debug_log(f"Has complimentary fragment: {state['has_complimentary']}")
                debug_log(f"Saving complimentary fragment: {first_song_in_mix.get('title')}-{first_song_in_mix.get('artist')}")
                self.audio_processor.save_to_history(first_song_in_mix.get("title"), first_song_in_mix.get("artist"), "") #to know dj about the played song
            else:
                state["selected_sound_fragment"] = song_list[0]
                state["complimentary_sound_fragment"] = {}
                state["has_complimentary"] = False

            song = state["selected_sound_fragment"]
            state["title"] = song.get("title")
            state["artist"] = song.get("artist")
            state["genres"] = song.get("genres", [])
            state["song_description"] = song.get("description", "")
        else:
            state["selected_sound_fragment"] = {}
            state["complimentary_sound_fragment"] = {}
            state["has_complimentary"] = False
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
        return state

    @staticmethod
    async def _build_song_intro(state: DJState) -> DJState:
        state["draft_text"] += f"\nNow playing: \"{state['title']}\" by {state['artist']}"
        if state["song_description"]:
            state["draft_text"] += f"\nDescription: {state['song_description']}"
        if state["genres"]:
            state["draft_text"] += f"\nGenres: {', '.join(state['genres'])}"
        if state["history"]:
            prev = state["history"][-1]
            intro = prev.get("introSpeech", "")
            state["draft_text"] += f"\nHistory (optional): Played \"{prev.get('title')}\" by {prev.get('artist')}."
            if intro:
                state["draft_text"] += f" Last intro speech was: {intro}"
        if state["context"]:
            if isinstance(state["context"], list) and len(state["context"]) == 1 and isinstance(state["context"][0],
                                                                                                dict):
                ctx_lines = [f"{k}: {v}" for k, v in state["context"][0].items() if v]
                ctx_text = ", ".join(ctx_lines)
            else:
                ctx_text = str(state["context"])
            state["draft_text"] += f"\nAtmosphere hint (optional): {ctx_text}"
        return state

    @staticmethod
    async def _combine_draft(state: DJState) -> DJState:
        state["draft_text"] = state["draft_text"].strip()
        return state

    async def _embellish(self, state: DJState) -> DJState:

        base_prompt = self.agent_config["prompt"].format(
            ai_dj_name=self.ai_dj_name,
            brand=self.brand,
        )

        full_prompt = f"""{base_prompt}
                       Draft:
                           {state["draft_text"]}
                       """

        messages = [
            {"role": "system", "content": "Generate plain text"},
            {"role": "user", "content": full_prompt}
        ]

        allow_search = (
                "Advertisement:" not in state["draft_text"]
                and state["title"] != "Unknown"
                and not state["genres"]
                and not state["song_description"]
        )

        if allow_search:
            debug_log(f"Internet search enabled for '{state['title']}' by {state['artist']}")
            tools = [InternetMCP.get_tool_definition(default_engine=self.search_engine)]
        else:
            debug_log("Internet search skipped (sufficient metadata or ad case)")
            tools = None

        response = await self.llm.ainvoke(messages=messages, tools=tools)

        try:
            debug_log(f"Raw ========== :\n{state['draft_text']}")
            llm_response = LlmResponse.from_response(response, self.llm_type)
            state["introduction_text"] = llm_response.actual_result
            debug_log(f"Embellished >>>>>>>>>>>>>>> : {state['introduction_text']}")
            self._reset_message(state["messages"])
            self._reset_event(state["events"])
        except Exception as e:
            self.logger.error(f"LLM Response parsing failed: {e}")
            state["introduction_text"] = state["draft_text"]
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        try:
            audio_data, reason = await self.audio_processor.generate_tts_audio(
                state["introduction_text"], state["title"], state["artist"]
            )
            self.audio_processor.save_to_history(state["title"], state["artist"], state["introduction_text"]) #even precorded case wil get to story (cprght issue)
            state["audio_data"] = audio_data
            if audio_data:
                target_dir = "/home/kneobroadcaster/merged"
                os.makedirs(target_dir, exist_ok=True)
                chosen_ext = "mp3"
                if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
                    chosen_ext = "wav"
                file_name = f"mixpla_{uuid.uuid4().hex}.{chosen_ext}"
                path = os.path.join(target_dir, file_name)
                with open(path, "wb") as f:
                    f.write(audio_data)
                state["file_path"] = path
                debug_log(f"Audio saved to: {path}")
        except Exception as e:
            self.logger.error(f"Error creating audio: {e}")
            state["file_path"] = None
        return state

    async def _broadcast_audio(self, state: DJState) -> DJState:
        try:
            if state.get("file_path") and state.get("selected_sound_fragment"):
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
                state["broadcast_success"] = result
                state["broadcast_message"] = (
                    f"Broadcasted: {state['title']} by {state['artist']}" if result else "Broadcast failed"
                )
                debug_log(f"Broadcast result: {state['broadcast_success']}")
            else:
                state["broadcast_success"] = False
                state["broadcast_message"] = "No audio or fragment to broadcast"
        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}")
            state["broadcast_success"] = False
        return state

    async def run(self, brand: str, memory_data: Dict[str, Any]) -> Tuple[bool, str, str, str, str]:
        initial_state = {
            "brand": brand,
            "events": memory_data.get("events", []),
            "history": memory_data.get("history", []),
            "context": memory_data.get("environment", []),
            "selected_sound_fragment": {},
            "complimentary_sound_fragment": {},
            "has_complimentary": False,
            "introduction_text": "",
            "draft_text": "",
            "audio_data": None,
            "title": memory_data.get("title", "Unknown"),
            "artist": memory_data.get("artist", "Unknown"),
            "genres": memory_data.get("genres", []),
            "song_description": memory_data.get("song_description", ""),
            "listeners": memory_data.get("listeners", []),
            "messages": memory_data.get("messages", []),
            "file_path": None,
            "broadcast_success": False,
            "broadcast_message": ""
        }

        result = await self.graph.ainvoke(initial_state)
        return (
            result["broadcast_success"],
            result["selected_sound_fragment"].get("id", "Unknown"),
            result["title"],
            result["artist"],
            result.get("broadcast_message", "")
        )

    def _reset_message(self, messages):
        if messages:
            for msg in messages:
                msg_id = msg.get("id")
                if msg_id:
                    self.memory.reset_message_by_id(msg_id)


    def _reset_event(self, events):
        if events:
            for ev in events:
                ev_id = ev.get("id")
                if ev_id:
                    self.memory.reset_event_by_id(ev_id)
