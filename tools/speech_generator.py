#!/usr/bin/env python3
# tools/speech_generator.py - Simplified Speech Generator tool

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import time

# Import ElevenLabs
from elevenlabs.client import ElevenLabs
from tools.base_tool import BaseTool


def get_capabilities() -> List[str]:
    return [
        "generate_speech",
        "generate_song_introduction"
    ]


class SpeechGenerator(BaseTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.output_dir = self.config.get("output_dir", "data/speech")

        # Hardcoded voice for simplicity
        self.voice_id = "EXAVITQu4vr4xnSDxMaL"  # Example voice ID - replace with preferred voice

        # Initialize ElevenLabs client
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        if self.elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
            self.logger.warning("ELEVENLABS_API_KEY not found in environment. Falling back to placeholder.")
            self.elevenlabs_client = None

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    @property
    def name(self) -> str:
        return "speech_generator"

    @property
    def description(self) -> str:
        return "Generates song introductions and announcements using ElevenLabs TTS."

    @property
    def category(self) -> str:
        return "presentation"

    def generate_speech(self, text: str, brand_id: str = None) -> str:
        """Generate speech audio from text."""
        # Get brand info if available
        brand = self.brand_manager.get_brand(brand_id) if brand_id and self.brand_manager else None
        brand_slug = brand.slugName if brand else brand_id

        # Create brand-specific directory
        brand_dir = os.path.join(self.output_dir, brand_slug) if brand_slug else self.output_dir
        os.makedirs(brand_dir, exist_ok=True)

        # Create a unique file name based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"speech_{timestamp}.mp3"
        file_path = os.path.join(brand_dir, file_name)

        # Generate the speech file
        success = self._generate_speech_file(text, file_path)

        if success:
            self.logger.info(f"Brand {brand_slug} - Generated speech: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        else:
            self.logger.error(f"Brand {brand_slug} - Failed to generate speech")

        return file_path

    def generate_song_introduction(self, song_info: Dict[str, Any], brand_id: str = None) -> str:
        """Generate an introduction for a song."""
        # Extract song information
        title = song_info.get("title", "Unknown Title")
        artist = song_info.get("artist", "Unknown Artist")
        album = song_info.get("album", "")

        # Create the introduction text
        intro_text = f"Now playing {title} by {artist}"
        if album:
            intro_text += f" from the album {album}"

        # Generate the speech
        return self.generate_speech(intro_text, brand_id)

    def _generate_speech_file(self, text: str, file_path: str) -> bool:
        try:
            if self.elevenlabs_client:
                # Use text_to_speech.convert instead of generate
                audio = self.elevenlabs_client.text_to_speech.convert(
                    text=text,
                    voice_id=self.voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )

                # Handle the generator correctly
                with open(file_path, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)

                return True
            else:
                return self._generate_placeholder(text, file_path)
        except Exception as e:
            self.logger.error(f"Failed to generate speech file: {e}")
            return False

    def _generate_placeholder(self, text: str, file_path: str) -> bool:
        """Generate a placeholder audio file for testing."""
        # Create a simple MP3 file
        try:
            with open(file_path, 'wb') as f:
                # Just write some placeholder data
                f.write(b'\x00' * 1000)

            self.logger.info(f"Generated placeholder speech file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate placeholder file: {e}")
            return False