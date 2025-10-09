import logging
import random
from pathlib import Path
from typing import List, Optional, Tuple
import os
import uuid
import shutil

from elevenlabs import ElevenLabs

from util.filler_generator import FillerGenerator


class Prerecorded:
    DEFAULT_FILLER_PROMPTS = [
        "Eerie mood music with smooth transition, 4-6 seconds",
        "Eerie ambient music with gentle fade out, 4-6 seconds",
        "Huge epic braam with natural decay, 4-6 seconds",
        "Deep epic braam with gradual fade, 4-6 seconds",
        "Massive cinematic braam with soft ending, 4-6 seconds",
    ]

    def __init__(self, elevenlabs_inst: ElevenLabs, brand: str):
        self.logger = logging.getLogger(__name__)
        self.fillers = self.DEFAULT_FILLER_PROMPTS
        self.filler_generator = FillerGenerator(elevenlabs_inst, Path("metadata") / brand)
        self.audio_files = self._load_audio_files()


    def _load_audio_files(self) -> List[Path]:
        audio_files = self.filler_generator.load_audio_files()
        if not audio_files:
            self.logger.info("Generating filler files...")
            self.filler_generator.generate_filler_files(self.fillers)
            audio_files = self.filler_generator.load_audio_files()
        return audio_files


    async def get_prerecorded_audio(self) -> Tuple[Optional[bytes], str, str]:
        if not self.audio_files:
            return None, "No prerecorded files available", ""

        try:
            selected_file = random.choice(self.audio_files)
            with open(selected_file, "rb") as f:
                audio_data = f.read()

            self.logger.info(f"Using prerecorded audio: {selected_file}")
            return audio_data, "Used pre-recorded audio", selected_file.suffix.lstrip('.')

        except Exception as e:
            self.logger.error(f"Error reading audio file: {e}")
            return None, f"Failed to load prerecorded: {e}", ""

    async def get_prerecorded_file_path(self, target_dir: str = "/home/kneobroadcaster/to_merge_filler") -> Tuple[Optional[str], str]:
        if not self.audio_files:
            return None, "No prerecorded files available"
        try:
            selected_file = random.choice(self.audio_files)
            os.makedirs(target_dir, exist_ok=True)
            ext = selected_file.suffix.lstrip('.').lower() or "mp3"
            if ext not in ("mp3", "wav"):
                ext = "mp3"
            file_name = f"temp_prerecorded_{uuid.uuid4().hex}.{ext}"
            dest_path = Path(target_dir) / file_name
            shutil.copy(selected_file, dest_path)
            self.logger.info(f"Using prerecorded audio: {selected_file} -> {dest_path}")
            return str(dest_path), "Used pre-recorded audio"
        except Exception as e:
            self.logger.error(f"Error preparing prerecorded file: {e}")
            return None, f"Failed to prepare prerecorded: {e}"