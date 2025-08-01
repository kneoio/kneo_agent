import logging
import random
from pathlib import Path
from typing import List, Optional, Tuple

from elevenlabs import ElevenLabs

from util.filler_generator import FillerGenerator


class Prerecorded:
    def __init__(self,elevenlabs_inst: ElevenLabs, fillers,  brand: str):
        self.logger = logging.getLogger(__name__)
        self.fillers = fillers
        self.filler_generator = FillerGenerator(elevenlabs_inst,  Path("metadata") / brand)
        self.audio_files = self._load_audio_files()

    def _load_audio_files(self) -> List[Path]:
        audio_files = self.filler_generator.load_audio_files()
        if not audio_files:
            self.logger.info("Generating filler files...")
            self.filler_generator.generate_filler_files(self.fillers)
            audio_files = self.filler_generator.load_audio_files()
        return audio_files


    async def get_prerecorded_audio(self) -> Tuple[Optional[bytes], str]:
        if not self.audio_files:
            return None, "No prerecorded files available"

        try:
            selected_file = random.choice(self.audio_files)
            with open(selected_file, "rb") as f:
                audio_data = f.read()

            self.logger.info(f"Using prerecorded audio: {selected_file}")
            return audio_data, "Used pre-recorded audio"

        except Exception as e:
            self.logger.error(f"Error reading audio file: {e}")
            return None, f"Failed to load prerecorded: {e}"