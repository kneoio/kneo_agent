import logging
import random
from pathlib import Path
from typing import List, Optional, Tuple

from util.filler_generator import FillerGenerator


class Prerecorded:
    def __init__(self, filler_generator: FillerGenerator, talkativity: float = 0.5):
        self.filler_generator = filler_generator
        self.logger = logging.getLogger(__name__)

        self.audio_files = self._load_audio_files()
        self.prerecorded_probability = 1.0 - float(talkativity)

    def _load_audio_files(self) -> List[Path]:
        audio_files = self.filler_generator.load_audio_files()
        if not audio_files:
            self.logger.info("Generating filler files...")
            self.filler_generator.generate_filler_files()
            audio_files = self.filler_generator.load_audio_files()
        return audio_files

    def should_use_prerecorded(self) -> bool:
        return self.audio_files and random.random() < self.prerecorded_probability

    async def get_prerecorded_audio(self) -> Tuple[Optional[bytes], str]:
        """Get prerecorded audio data"""
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