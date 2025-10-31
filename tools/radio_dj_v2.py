import json
import logging
import os
from datetime import datetime
from typing import Tuple

from langgraph.graph import StateGraph, END

from cnst.llm_types import LlmType
from mcp.queue_mcp import QueueMCP
from mcp.server.llm_response import LlmResponse
from models.live_container import LiveRadioStation
from tools.dj_state import DJState
from util.file_util import debug_log


class RadioDJV2:
    def __init__(self, station: LiveRadioStation, audio_processor,
                 mcp_client=None, debug=False, llm_client=None, llm_type=LlmType.CLAUDE):
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
        self.audio_processor = audio_processor
        self.station = station
        self.brand = station.slugName
        self.queue_mcp = QueueMCP(mcp_client)
        self.target_dir = "/home/kneobroadcaster/to_merge"
        os.makedirs(self.target_dir, exist_ok=True)
        self.graph = self._build_graph()
        debug_log(f"RadioDJV2 initialized with llm={self.llm_type}, songsCount={self.station.songsCount}")

    async def run(self) -> Tuple[bool, str, str]:
        self.logger.info(f"---------------------Interaction started ------------------------------")
        
        initial_state = {
            "brand": self.brand,
            "intro_texts": [],
            "audio_file_paths": [],
            "song_ids": [],
            "broadcast_success": False
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
        debug_log("RadioDJV2 graph workflow built")
        return workflow.compile()


    async def _generate_intro(self, state: DJState) -> DJState:

        for idx, prompt_item in enumerate(self.station.prompt.prompts):
            draft = prompt_item.draft or ""
            full_prompt = f"{prompt_item.prompt}\n\nInput:\n{draft}"
            
            response = await self.llm.ainvoke(messages=[{"role": "user", "content": full_prompt}])
            
            llm_response = LlmResponse.parse_plain_response(response, self.llm_type)
            intro_text = llm_response.actual_result
            
            state["intro_texts"].append(intro_text)
            state["song_ids"].append(prompt_item.songId)
            
            self.ai_logger.info(f"{self.brand} INTRO {idx+1}: {intro_text}")
            debug_log(f"Generated intro {idx+1} for {self.brand}")
        
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        if not state["intro_texts"]:
            self.logger.warning("No intro texts to generate audio for")
            return state

        for idx, intro_text in enumerate(state["intro_texts"]):
            try:
                try:
                    json.loads(intro_text)
                    audio_data, reason = await self.audio_processor.generate_tts_dialogue(intro_text)
                except json.JSONDecodeError:
                    audio_data, reason = await self.audio_processor.generate_tts_audio(intro_text)

                if audio_data:
                    time_tag = datetime.now().strftime("%Hh%Mm%Ss")
                    short_name = f"{self.brand}_intro{idx+1}_{time_tag}"
                    file_path = self._save_audio_file(audio_data, short_name)
                    state["audio_file_paths"].append(file_path)
                    debug_log(f"Audio {idx+1} saved: {file_path}")
                else:
                    self.logger.warning(f"No audio generated for intro {idx+1}: {reason}")

            except Exception as e:
                self.logger.error(f"Error creating audio {idx+1}: {e}")

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
            
            if num_songs == 1:
                result = await self.queue_mcp.add_to_queue_i_s(
                    brand_name=self.brand,
                    sound_fragment_uuid=state["song_ids"][0],
                    file_path=state["audio_file_paths"][0],
                    priority=10
                )
            elif num_songs == 2:
                result = await self.queue_mcp.add_to_queue_i_s_i_s(
                    brand_name=self.brand,
                    fragment_uuid_1=state["song_ids"][0],
                    fragment_uuid_2=state["song_ids"][1],
                    file_path_1=state["audio_file_paths"][0],
                    file_path_2=state["audio_file_paths"][1],
                    priority=10
                )
            else:
                self.logger.error(f"Unexpected number of songs: {num_songs}")
                state["broadcast_success"] = False
                return state

            debug_log(f"Broadcast result: {result}")
            state["broadcast_success"] = bool(result is True or (isinstance(result, dict) and result.get("success")))

        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}")
            state["broadcast_success"] = False

        return state
