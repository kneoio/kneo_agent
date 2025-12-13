import logging
import os
from datetime import datetime
from typing import Tuple

from langgraph.graph import StateGraph, END

from cnst.llm_types import LlmType
from llm.llm_request import invoke_intro
from llm.llm_response import LlmResponse
from memory.brand_memory_manager import BrandMemoryManager
from models.live_container import LiveRadioStation
from tools.dj_state import DJState
from tools.queue_sync import enqueue
from repos.brand_memory_repo import brand_memory_repo


class RadioDJV2:
    memory_manager = BrandMemoryManager()

    def __init__(self, station: LiveRadioStation, audio_processor, target_dir: str,
                 llm_client=None, llm_type=LlmType.GROQ, db_pool=None):
        if db_pool is None:
            raise ValueError("db_pool parameter is required for RadioDJV2 initialization")

        self.llm_type = llm_type
        self.logger = logging.getLogger(__name__)
        self.ai_logger = logging.getLogger("tools.interaction_tools.ai")
        self.llm = llm_client
        self.audio_processor = audio_processor
        self.live_station = station
        self.brand = station.slugName
        self.target_dir = target_dir
        self.db = db_pool
        #self.user_summary = BrandUserSummarizer(self.db, self.llm, llm_type)
        self.graph = self._build_graph()

    async def run(self) -> Tuple[bool, str, str]:
        self.logger.info(f"---------------------Interaction started ------------------------------")
        self.ai_logger.info(f"{self.brand} - Start ---------------------------------")
        initial_state = {
            "brand": self.brand,
            "intro_texts": [],
            "audio_file_paths": [],
            "song_ids": [],
            "broadcast_success": False,
            "dialogue_states": []
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
        memory_entries = RadioDJV2.memory_manager.get(self.brand)
        memory_texts = [entry["text"] for entry in memory_entries if isinstance(entry, dict) and "text" in entry]
        
        summary_text = ""
        try:
            from datetime import date
            db_summary = await brand_memory_repo.get(self.brand, date.today())
            if db_summary and db_summary.summary:
                summary_text = db_summary.summary.get("summary", "")
        except Exception as e:
            self.logger.warning(f"Failed to load database summary for brand {self.brand}: {e}")
        
        if summary_text.strip():
            raw_mem = f"Recent Summary: {summary_text}\n\nRecent Interactions:\n" + "\n".join(memory_texts)
        else:
            raw_mem = "\n".join(memory_texts)
        
        for idx, prompt_item in enumerate(self.live_station.prompts):
            draft = prompt_item.draft or ""
            self.ai_logger.info(f"{self.brand} LLM: {self.llm_type.name}, DIALOGUE SETTING{idx + 1}: {prompt_item.dialogue}")
            self.ai_logger.info(f"{self.brand} DRAFT: {draft}")
            self.ai_logger.info(f"{self.brand} PROMPT: {prompt_item.prompt[:80]}...")

            raw_response = await invoke_intro(
                llm_client=self.llm,
                prompt=prompt_item.prompt,
                draft=draft,
                on_air_memory=raw_mem
            )
            
            if prompt_item.dialogue:
                response = LlmResponse.parse_structured_response(raw_response, self.llm_type)
            else:
                response = LlmResponse.parse_plain_response(raw_response, self.llm_type)
            
            state["intro_texts"].append(response.actual_result)
            state["song_ids"].append(prompt_item.songId)
            state["dialogue_states"].append(prompt_item.dialogue)
            if not prompt_item.dialogue:
                RadioDJV2.memory_manager.add(self.brand, response.actual_result)

            self.ai_logger.info(f"{self.brand} RESULT{idx + 1}: {response.actual_result}")

        return state

    async def _create_audio(self, state: DJState) -> DJState:
        if not state["intro_texts"]:
            self.logger.warning("No intro texts to generate audio for")
            return state

        for idx, (intro_text, is_dialogue) in enumerate(zip(state["intro_texts"], state["dialogue_states"])):

            try:
                self.ai_logger.info(f"{self.brand} DIALOGUE MODE: {is_dialogue} for intro {idx + 1}")

                if is_dialogue:
                    audio_data, reason = await self.audio_processor.generate_tts_dialogue(intro_text)
                else:
                    audio_data, reason = await self.audio_processor.generate_tts_audio(intro_text)

                if audio_data:
                    time_tag = datetime.now().strftime("%Hh%Mm%Ss")
                    short_name = f"{self.brand}_intro{idx + 1}_{time_tag}"
                    file_path = self._save_audio_file(audio_data, short_name)
                    state["audio_file_paths"].append(file_path)
                    self.ai_logger.info(f"{self.brand} AUDIO: {idx + 1}: {file_path}")
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
            expected_start_time = next(
                (p.startTime for p in self.live_station.prompts
                 if getattr(p, "oneTimeRun", False) and getattr(p, "startTime", None)),
                None
            )

            priority = 9 if expected_start_time is not None else 10

            if num_songs == 1:
                result = await enqueue(
                    brand=self.brand,
                    merging_method="INTRO_SONG",
                    sound_fragments={"song1": state["song_ids"][0]},
                    file_paths={"audio1": state["audio_file_paths"][0]},
                    priority=priority
                )
            elif num_songs == 2:
                result = await enqueue(
                    brand=self.brand,
                    merging_method="INTRO_SONG_INTRO_SONG",
                    sound_fragments={"song1": state["song_ids"][0], "song2": state["song_ids"][1]},
                    file_paths={"audio1": state["audio_file_paths"][0], "audio2": state["audio_file_paths"][1]},
                    priority=priority
                )
            else:
                self.logger.error(f"Unexpected number of songs: {num_songs}")
                state["broadcast_success"] = False
                return state

            state["broadcast_success"] = bool(
                result is True or (isinstance(result, dict) and result.get("success"))
            )

            self.ai_logger.info(f"{self.brand} RESULT: {state['broadcast_success']}")
            self.ai_logger.info(f"{self.brand} - End ---------------------------------")

        except Exception as e:
            self.logger.error(f"Error broadcasting audio: {e}")
            state["broadcast_success"] = False

        return state

    async def _load_brand_summary(self):
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT summary FROM mixpla__brand_memory WHERE brand = $1 ORDER BY day DESC LIMIT 1",
                self.brand
            )
            return row
