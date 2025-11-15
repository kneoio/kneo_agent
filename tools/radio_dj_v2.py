import json
import logging
import os
from datetime import datetime
from typing import Tuple

from langgraph.graph import StateGraph, END

from cnst.llm_types import LlmType
from llm.llm_request import invoke_intro
from mcp.queue_mcp import QueueMCP
from models.live_container import LiveRadioStation
from tools.dj_state import DJState


class RadioDJV2:
    def __init__(self, station: LiveRadioStation, audio_processor, target_dir: str,
                 mcp_client=None, llm_client=None, llm_type=LlmType.GROQ):
        self.llm_type = llm_type
        self.logger = logging.getLogger(__name__)
        self.ai_logger = logging.getLogger("tools.interaction_tools.ai")
        self.llm = llm_client
        self.audio_processor = audio_processor
        self.live_station = station
        self.brand = station.slugName
        self.queue_mcp = QueueMCP(mcp_client)
        self.target_dir = target_dir
        self.graph = self._build_graph()

    async def run(self) -> Tuple[bool, str, str]:
        self.logger.info(f"---------------------Interaction started ------------------------------")
        self.ai_logger.info(f"{self.brand} ---- Interaction started ----")
        initial_state = {
            "brand": self.brand,
            "intro_texts": [],
            "audio_file_paths": [],
            "song_ids": [],
            "broadcast_success": False,
            "dialogue": False
        }

        result = await self.graph.ainvoke(initial_state)
        return result["broadcast_success"], self.brand, ""

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)

        workflow.add_node("generate_intro", self._generate_intro)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("broadcast_audio", self._broadcast_audio)

        workflow.set_entry_point("generate_intro")
        workflow.add_edge("generate_intro", "create_audio")
        workflow.add_edge("create_audio", "broadcast_audio")
        workflow.add_edge("broadcast_audio", END)
        return workflow.compile()

    async def _generate_intro(self, state: DJState) -> DJState:

        for idx, prompt_item in enumerate(self.live_station.prompts):
            draft = prompt_item.draft or ""
            self.ai_logger.info(f"{self.brand} LLM: {self.llm_type.name} DRAFT: {draft}")
            self.ai_logger.info(f"{self.brand} PROMPT: {prompt_item.prompt}")
            intro_text = await invoke_intro(self.llm, prompt_item.prompt, draft, self.llm_type)

            state["intro_texts"].append(intro_text.actual_result)
            state["song_ids"].append(prompt_item.songId)
            state["dialogue"] = prompt_item.dialogue

            self.ai_logger.info(f"{self.brand} INTRO {idx + 1}: {intro_text}")

        return state

    async def _create_audio(self, state: DJState) -> DJState:
        if not state["intro_texts"]:
            self.logger.warning("No intro texts to generate audio for")
            return state

        for idx, intro_text in enumerate(state["intro_texts"]):
            try:
                if state["dialogue"]:
                    audio_data, reason = await self.audio_processor.generate_tts_dialogue(intro_text)
                else:
                    audio_data, reason = await self.audio_processor.generate_tts_audio(intro_text)

                if audio_data:
                    time_tag = datetime.now().strftime("%Hh%Mm%Ss")
                    short_name = f"{self.brand}_intro{idx + 1}_{time_tag}"
                    file_path = self._save_audio_file(audio_data, short_name)
                    state["audio_file_paths"].append(file_path)
                else:
                    self.logger.warning(f"No audio generated for intro {idx + 1}: {reason}")

            except Exception as e:
                self.logger.error(f"Error creating audio {idx + 1}: {e}")

        return state

    def _save_audio_file(self, audio_data: bytes, short_name: str) -> str:
        chosen_ext = "mp3"
        if audio_data[:4] == b"RIFF" and audio_data[8:12] == b"WAVE":
            chosen_ext = "wav"

        file_name = f"{short_name}.{chosen_ext}"
        path = os.path.join(self.target_dir, file_name)
        with open(path, "wb") as f:
            f.write(audio_data)
        return path

    async def _broadcast_audio(self, state: DJState) -> DJState:
        try:
            if not state["audio_file_paths"]:
                self.logger.warning("No audio files to broadcast")
                state["broadcast_success"] = False
                return state

            num_songs = len(state["audio_file_paths"])
            expected_start_time = next((p.startTime for p in self.live_station.prompts if
                                      getattr(p, "oneTimeRun", False) and getattr(p, "startTime", None)), None)
            priority = 9 if expected_start_time is not None else 10

            if num_songs == 1:
                result = await self.queue_mcp.add_to_queue_i_s(
                    brand_name=self.brand,
                    sound_fragment_uuid=state["song_ids"][0],
                    file_path=state["audio_file_paths"][0],
                    priority=priority
                )
            elif num_songs == 2:
                result = await self.queue_mcp.add_to_queue_i_s_i_s(
                    brand_name=self.brand,
                    fragment_uuid_1=state["song_ids"][0],
                    fragment_uuid_2=state["song_ids"][1],
                    file_path_1=state["audio_file_paths"][0],
                    file_path_2=state["audio_file_paths"][1],
                    priority=priority
                )
            else:
                self.logger.error(f"Unexpected number of songs: {num_songs}")
                state["broadcast_success"] = False
                return state

            state["broadcast_success"] = bool(result is True or (isinstance(result, dict) and result.get("success")))

        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}")
            state["broadcast_success"] = False

        return state
