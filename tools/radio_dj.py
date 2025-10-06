import logging
import os
import uuid
from typing import Dict, Any, Tuple

from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from api.queue import Queue
from cnst.llm_types import LlmType
from cnst.play_list_item_type import PlaylistItemType
from mcp.external.internet_mcp import InternetMCP
from mcp.queue_mcp import QueueMCP
from mcp.server.llm_response import LlmResponse
from mcp.sound_fragment_mcp import SoundFragmentMCP
from models.sound_fragment import SoundFragment
from tools.dj_state import DJState, MergingType
from tools.draft_builder import build_draft, build_ad_intro_text
from util.file_util import debug_log
from util.randomizer import get_random_merging_type


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
        self.target_dir = "/home/kneobroadcaster/to_merge"
        os.makedirs(self.target_dir, exist_ok=True)
        self.graph = self._build_graph()
        debug_log(f"RadioDJ v2 initialized with llm={self.llm_type}")

    async def run(self, brand: str, memory_data: Dict[str, Any]) -> Tuple[bool, str, str]:
        initial_state = {
            "brand": brand,
            "events": memory_data.get("events", []),
            "messages": memory_data.get("messages", []),
            "history": memory_data.get("history", []),
            "context": memory_data.get("environment", []),
            "song_fragments": [],
            "broadcast_success": False,
            "session_id": uuid.uuid4().hex
        }

        result = await self.graph.ainvoke(initial_state)

        song = result["song_fragments"][0]
        return result["broadcast_success"], song.title, song.artist

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)

        workflow.add_node("fetch_song_fragment", self._fetch_song_fragment)
        workflow.add_node("build_song_intro", self._build_song_intro)
        workflow.add_node("build_ad_intro", self._build_ad_intro)
        workflow.add_node("embellish", self._embellish)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("fetch_song_fragment")

        workflow.add_conditional_edges(
            "fetch_song_fragment",
            lambda state: "build_ad_intro"
            if any(ev.get("type") == "AD" for ev in state["events"])
            else "build_song_intro",
            {"build_ad_intro": "build_ad_intro", "build_song_intro": "build_song_intro"},
        )

        workflow.add_conditional_edges(
            "build_ad_intro",
            lambda state: "end" if state.get("__end__") else "embellish",
            {"end": END, "embellish": "embellish"},
        )

        workflow.add_conditional_edges(
            "build_song_intro",
            lambda state: "broadcast_audio"
            if state.get("merging_type") == MergingType.SONG_CROSSFADE_SONG
            else "embellish",
            {"broadcast_audio": "broadcast_audio", "embellish": "embellish"},
        )

        workflow.add_edge("embellish", "create_audio")
        workflow.add_edge("create_audio", "broadcast_audio")
        workflow.add_edge("broadcast_audio", END)

        debug_log("Graph workflow built")
        return workflow.compile()

    async def _build_ad_intro(self, state: DJState) -> DJState:
        ad_list = await self.sound_fragments_mcp.get_brand_sound_fragment(
            brand=self.brand,
            fragment_type=PlaylistItemType.ADVERTISEMENT.value
        )
        if ad_list:
            ad = SoundFragment.from_dict(ad_list[0])
            ad.draft_intro = build_ad_intro_text(ad.title, ad.artist)
            state["song_fragments"] = [ad]
        else:
            self.logger.warning("No advertisement fragment available — skipping ad broadcast")
            state["broadcast_success"] = False
            state["__end__"] = True
        self._reset_event(state["events"])
        return state

    async def _fetch_song_fragment(self, state: DJState) -> DJState:
        fragment_dicts = await self.sound_fragments_mcp.get_brand_sound_fragment(self.brand)
        state["song_fragments"] = [SoundFragment.from_dict(d) for d in (fragment_dicts or [])][:2]

        if state["song_fragments"]:
            first = state["song_fragments"][0]
            debug_log(f"Fetched {len(state['song_fragments'])} fragments, first: {first.title}-{first.artist}")
        else:
            self.logger.warning("No song fragments found")
        return state

    async def _build_song_intro(self, state: DJState) -> DJState:
        for song in state["song_fragments"]:
            song.draft_intro = build_draft(
                title=song.title,
                artist=song.artist,
                ai_dj_name=self.ai_dj_name,
                brand=self.brand,
                song_description=song.description,
                genres=song.genres,
                history=state["history"],
                context=state["context"]
            )

        if len(state["song_fragments"]) == 1:
            state["merging_type"] = MergingType.INTRO_SONG
        else:
            state["merging_type"] = get_random_merging_type()

        debug_log(f"Merging chosen: {state['merging_type'].name}")
        return state

    async def _embellish(self, state: DJState) -> DJState:
        targets = []
        if state["merging_type"] == MergingType.INTRO_SONG and len(state["song_fragments"]) >= 1:
            targets = [state["song_fragments"][0]]
        elif state["merging_type"] == MergingType.SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][1]]
        elif state["merging_type"] == MergingType.INTRO_SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][0], state["song_fragments"][1]]

        for song in targets:
            draft = song.draft_intro or ""
            full_prompt = f"{self.agent_config['prompt']}\n\nInput:\n{draft}"

            prompt_messages = [
                {"role": "system", "content": "Generate plain text"},
                {"role": "user", "content": full_prompt}
            ]

            allow_search = (
                song.type != PlaylistItemType.ADVERTISEMENT.value
                and not song.genres
                and not song.description
            )
            tools = [InternetMCP.get_tool_definition(default_engine=self.search_engine)] if allow_search else None

            response = await self.llm.ainvoke(messages=prompt_messages, tools=tools)
            try:
                llm_response = LlmResponse.from_response(response, self.llm_type)
                song.introduction_text = llm_response.actual_result
                debug_log(f"Embellished intro for {song.title}: {song.introduction_text}")
                self.ai_logger.info(
                    f"{self.brand} FINAL_RESULT: {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n"
                )
            except Exception as e:
                self.logger.error(f"LLM Response parsing failed for {song.title}: {e}")
                song.introduction_text = draft

        self._reset_message(state.get("messages"))
        self._reset_event(state.get("events"))
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        if state["merging_type"] == MergingType.INTRO_SONG and len(state["song_fragments"]) >= 1:
            targets = [state["song_fragments"][0]]
        elif state["merging_type"] == MergingType.SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][1]]
        elif state["merging_type"] == MergingType.INTRO_SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][0], state["song_fragments"][1]]
        else:
            targets = []

        for idx, song in enumerate(targets):
            try:
                text = song.introduction_text
                if not text:
                    continue
                audio_data, reason = await self.audio_processor.generate_tts_audio(text)
                if audio_data:
                    short_id = song.id.replace("-", "")[:8]
                    if state["merging_type"] == MergingType.INTRO_SONG_INTRO_SONG:
                        role = f"intro{idx + 1}_{short_id}"
                    else:
                        role = f"{idx}_{short_id}"
                    short_name = f"{state['session_id']}_{state['merging_type'].name[:4].lower()}_{role}"
                    self._save_audio_file(song, audio_data, state, short_name)
            except Exception as e:
                self.logger.error(f"Error creating audio for {song.title}: {e}")

    def _save_audio_file(self, song: SoundFragment, audio_data: bytes, state: DJState, short_name: str) -> None:
        song.audio_data = audio_data

        chosen_ext = "mp3"
        if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            chosen_ext = "wav"

        file_name = f"{short_name}.{chosen_ext}"
        path = os.path.join(self.target_dir, file_name)
        with open(path, "wb") as f:
            f.write(audio_data)
        song.file_path = path
        debug_log(f"Audio saved for {song.title} [{state['merging_type'].name}]: {path}")

    async def _broadcast_audio(self, state: DJState) -> DJState:
        try:
            if not state["song_fragments"]:
                state["broadcast_success"] = False
                return state

            if state["merging_type"] == MergingType.INTRO_SONG and state["song_fragments"][0].file_path:
                result = await self.queue_mcp.add_to_queue_i_s(
                    brand_name=self.brand,
                    sound_fragment_uuid=state["song_fragments"][0].id,
                    file_path=state["song_fragments"][0].file_path,
                    priority=10
                )

            elif state["merging_type"] == MergingType.SONG_INTRO_SONG and len(state["song_fragments"]) >= 2 and \
                    state["song_fragments"][1].file_path:
                result = await self.queue_mcp.add_to_queue_s_i_s(
                    brand_name=self.brand,
                    fragment_uuid_1=state["song_fragments"][0].id,
                    fragment_uuid_2=state["song_fragments"][1].id,
                    file_path=state["song_fragments"][1].file_path,
                    priority=10
                )

            elif state["merging_type"] == MergingType.INTRO_SONG_INTRO_SONG and len(state["song_fragments"]) >= 2 \
                    and state["song_fragments"][0].file_path and state["song_fragments"][1].file_path:
                result = await self.queue_mcp.add_to_queue_i_s_i_s(
                    brand_name=self.brand,
                    fragment_uuid_1=state["song_fragments"][0].id,
                    fragment_uuid_2=state["song_fragments"][1].id,
                    file_path_1=state["song_fragments"][0].file_path,
                    file_path_2=state["song_fragments"][1].file_path,
                    priority=10
                )

            elif state["merging_type"] == MergingType.SONG_CROSSFADE_SONG and len(state["song_fragments"]) >= 2:
                result = await self.queue_mcp.add_to_queue_crossfade(
                    brand_name=self.brand,
                    fragment_uuid_1=state["song_fragments"][0].id,
                    fragment_uuid_2=state["song_fragments"][1].id,
                    priority=10
                )

            else:
                result = False

            debug_log(state["broadcast_success"])
            state["broadcast_success"] = result


            try:
                for song in state["song_fragments"]:
                    intro_text = getattr(song, "introduction_text", "")
                    if intro_text:
                        history_entry = {
                            "title": song.title,
                            "artist": song.artist,
                            "introSpeech": intro_text
                        }
                        self.memory.store_conversation_history(history_entry)
            except Exception as e:
                self.logger.warning(f"Failed to save broadcast history: {e}")

        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}")
            state["broadcast_success"] = False

        return state

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
