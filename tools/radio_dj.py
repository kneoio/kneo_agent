import json
import logging
import os
import random
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple, Callable, Coroutine

from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from api.queue import Queue
from cnst.llm_types import LlmType
from mcp.queue_mcp import QueueMCP
from mcp.sound_fragment_mcp import SoundFragmentMCP
from models.sound_fragment import SoundFragment
from tools.ad_intro_builder import build_ad_intro
from tools.dj_state import DJState, MergingType
from tools.message_dialogue_builder import build_message_dialogue
from tools.mini_podcast_builder import build_mini_podcast
from tools.song_intro_builder import build_song_intro, embellish
from util.file_util import debug_log


class RadioDJ:
    build_ad_intro: Callable[['RadioDJ', DJState], Coroutine[Any, Any, DJState]]
    build_message_dialogue: Callable[['RadioDJ', DJState], Coroutine[Any, Any, DJState]]
    build_mini_podcast: Callable[['RadioDJ', DJState], Coroutine[Any, Any, DJState]]
    build_song_intro: Callable[['RadioDJ', DJState], Coroutine[Any, Any, DJState]]
    embellish: Callable[['RadioDJ', DJState], Coroutine[Any, Any, DJState]]

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
        self.preferredLang = self.agent_config.get("preferredLang")
        self.search_engine = self.agent_config.get("search_engine_type")
        self.ai_dj_name = self.agent_config.get("name")
        self.brand = brand
        self.sound_fragments_mcp = SoundFragmentMCP(mcp_client)
        self.queue_mcp = QueueMCP(mcp_client)
        self.target_dir = "/home/kneobroadcaster/to_merge"
        os.makedirs(self.target_dir, exist_ok=True)
        self.graph = self._build_graph()
        self.dialogue_probability = self.agent_config.get("podcastMode")
        debug_log(f"RadioDJ v2 initialized with llm={self.llm_type}")

    async def run(self, brand: str, memory_data: Dict[str, Any]) -> Tuple[bool, str, str]:
        self.ai_logger.info(f"---------------------Interaction started ------------------------------")
        self.logger.info(f"---------------------Interaction started ------------------------------")
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
        workflow.add_node("build_ad_intro", self.build_ad_intro)
        workflow.add_node("build_song_intro", self.build_song_intro)
        workflow.add_node("build_message_dialogue", self.build_message_dialogue)
        workflow.add_node("build_mini_podcast", self.build_mini_podcast)
        workflow.add_node("embellish", self.embellish)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("fetch_song_fragment")

        def next_after_fetch(state):
            if any(ev.get("type") == "AD" for ev in state["events"]):
                return "build_ad_intro"
            return "build_song_intro"

        def next_after_ad(state):
            if state.get("__end__"):
                return "end"
            return "embellish"

        def next_after_song_intro(state):
            if state.get("messages") and self.agent_config.get("messagePrompt"):
                return "build_message_dialogue"
            if (
                    self.agent_config.get("miniPodcastPrompt")
                    and state["song_fragments"]
                    and state["song_fragments"][0].description
                    and random.random() < getattr(state, "dialogue_probability", self.dialogue_probability)
            ):
                return "build_mini_podcast"
            if state.get("merging_type") == MergingType.SONG_CROSSFADE_SONG:
                return "broadcast_audio"
            return "embellish"

        workflow.add_conditional_edges(
            "fetch_song_fragment",
            next_after_fetch,
            {"build_ad_intro": "build_ad_intro", "build_song_intro": "build_song_intro"},
        )

        workflow.add_conditional_edges(
            "build_ad_intro",
            next_after_ad,
            {"end": END, "embellish": "embellish"},
        )

        workflow.add_conditional_edges(
            "build_song_intro",
            next_after_song_intro,
            {
                "build_message_dialogue": "build_message_dialogue",
                "build_mini_podcast": "build_mini_podcast",
                "broadcast_audio": "broadcast_audio",
                "embellish": "embellish",
            },
        )

        workflow.add_edge("build_message_dialogue", "create_audio")
        workflow.add_edge("build_mini_podcast", "create_audio")
        workflow.add_edge("embellish", "create_audio")
        workflow.add_edge("create_audio", "broadcast_audio")
        workflow.add_edge("broadcast_audio", END)

        debug_log("Graph workflow built")
        return workflow.compile()

    async def _fetch_song_fragment(self, state: DJState) -> DJState:
        fragment_dicts = await self.sound_fragments_mcp.get_brand_sound_fragment(self.brand)
        state["song_fragments"] = [SoundFragment.from_dict(d) for d in (fragment_dicts or [])][:2]

        if state["song_fragments"]:
            first = state["song_fragments"][0]
            debug_log(f"Fetched {len(state['song_fragments'])} fragments, first: {first.title}-{first.artist}")
        else:
            self.logger.warning("No song fragments found")
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        # todo targets should be filled ou earlier (architecture)
        if (state["merging_type"] == MergingType.INTRO_SONG or
            state["merging_type"] == MergingType.MINIPODCAST_SONG or
            state["merging_type"] == MergingType.MESSAGEDIALOG_INTRO_SONG) and len(state["song_fragments"]) >= 1:
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

                try:
                    json.loads(text)
                    audio_data, reason = await self.audio_processor.generate_tts_dialogue(text)
                except json.JSONDecodeError:
                    audio_data, reason = await self.audio_processor.generate_tts_audio(text)

                if audio_data:
                    short_id = song.id.replace("-", "")[:8]
                    time_tag = datetime.now().strftime("%Hh%Mm%Ss")
                    short_name = f"{state['merging_type'].name.lower()}_{short_id}_{time_tag}"
                    self._save_audio_file(song, audio_data, state, short_name)

            except Exception as e:
                self.logger.error(f"Error creating audio for {song.title}: {e}")

        return state

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

            if (state["merging_type"] == MergingType.INTRO_SONG or
                state["merging_type"] == MergingType.MINIPODCAST_SONG or
                state["merging_type"] == MergingType.MESSAGEDIALOG_INTRO_SONG) and state["song_fragments"][0].file_path:
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

            debug_log(result)
            state["broadcast_success"] = result
            state["broadcast_success"] = bool(result is True or (isinstance(result, dict) and result.get("success")))

            if state["broadcast_success"]:
                try:
                    for song in state["song_fragments"]:
                        history_entry = {
                            "relevantSoundFragmentId": song.id,
                            "title": song.title,
                            "artist": song.artist,
                            "introSpeech": song.introduction_text
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


RadioDJ.build_song_intro = build_song_intro
RadioDJ.embellish = embellish
RadioDJ.build_ad_intro = build_ad_intro
RadioDJ.build_mini_podcast = build_mini_podcast
RadioDJ.build_message_dialogue = build_message_dialogue
