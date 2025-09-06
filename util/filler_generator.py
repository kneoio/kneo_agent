# tools/filler_generator.py

import logging
from pathlib import Path
from elevenlabs.client import ElevenLabs


class FillerGenerator:
    def __init__(self, elevenlabs_inst: ElevenLabs, metadata_folder: Path):
        self.logger = logging.getLogger(__name__)
        self.elevenlabs_inst = elevenlabs_inst
        self.metadata_folder = metadata_folder
        self.metadata_folder.mkdir(parents=True, exist_ok=True)

    def generate_filler_files(self, fillers):
        if not fillers:
            self.logger.warning("No fillers found in agent configuration")
            return

        self.logger.info(f"Generating {len(fillers)} filler files for {self.metadata_folder.name}")

        for i, filler_prompt in enumerate(fillers):
            try:
                file_name = self.metadata_folder / f"filler_{i + 1:02d}.mp3"
                if file_name.exists():
                    self.logger.debug(f"Filler file {file_name} already exists, skipping")
                    continue

                self.logger.debug(f"Generating filler {i + 1}/{len(fillers)}: {filler_prompt}")
                effect = self.elevenlabs_inst.text_to_sound_effects.convert(
                    text=filler_prompt,
                )
                with open(file_name, "wb") as f:
                    for chunk in effect:
                        f.write(chunk)

                self.logger.info(f"Generated filler audio: {file_name}")

            except Exception as e:
                self.logger.error(f"Failed to generate filler {i + 1} ({filler_prompt}): {str(e)}")
                continue

        self.logger.info(f"Finished generating filler files for {self.metadata_folder.name}")

    def load_audio_files(self):
        audio_files = []
        if self.metadata_folder.exists() and self.metadata_folder.is_dir():
            for file in self.metadata_folder.glob("*.mp3"):
                audio_files.append(file)
            for file in self.metadata_folder.glob("*.wav"):
                audio_files.append(file)

        return audio_files
