import logging
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from elevenlabs.client import ElevenLabs

from api.interaction_memory import InteractionMemory
from tools.filler_generator import FillerGenerator


class AudioProcessor:
    """Handles audio generation and prerecorded files"""

    def __init__(self, tts_client: ElevenLabs, filler_generator: FillerGenerator,
                 agent_config: Dict[str, Any], memory: InteractionMemory):
        self.tts_client = tts_client
        self.filler_generator = filler_generator
        self.agent_config = agent_config
        self.memory = memory
        self.logger = logging.getLogger(__name__)

        # Load prerecorded audio files
        self.audio_files = self._load_audio_files()

        # Calculate probability for prerecorded vs generated content
        talkativity = self.agent_config.get("talkativity", 0.5)
        self.prerecorded_probability = 1.0 - float(talkativity)

    def _load_audio_files(self) -> List[Path]:
        """Load available prerecorded audio files"""
        audio_files = self.filler_generator.load_audio_files()
        if not audio_files and self.agent_config.get('fillers'):
            self.logger.info("Generating filler files...")
            self.filler_generator.generate_filler_files(self.agent_config.get('fillers'))
            audio_files = self.filler_generator.load_audio_files()
        return audio_files

    def should_use_prerecorded(self) -> bool:
        """Decide whether to use prerecorded audio"""
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

    async def generate_tts_audio(self, text: str, title: str, artist: str) -> Tuple[Optional[bytes], str]:
        """Generate TTS audio from text"""
        if not text:
            return None, "No text provided for TTS"

        # Check for copyright content
        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return await self.get_prerecorded_audio()

        try:
            # Save to history
            self._save_to_history(title, artist, text)

            # Generate TTS
            voice_id = self.agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')
            audio_stream = self.tts_client.text_to_speech.convert(
                voice_id=voice_id,
                text=text[:500],  # Limit text length
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            audio_data = b''.join(audio_stream)

            if audio_data:
                self.logger.info("TTS generation successful")
                return audio_data, f"Generated TTS using voice: {voice_id}"
            else:
                return None, "TTS conversion resulted in empty audio"

        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}")
            return None, f"TTS generation failed: {str(e)}"

    def _save_to_history(self, title: str, artist: str, text: str):
        """Save introduction to conversation history"""
        try:
            history_entry = {
                "title": title,
                "artist": artist,
                "content": text
            }
            success = self.memory.store_conversation_history(history_entry)
            if success:
                self.logger.info(f"Saved to history: '{title}' by {artist}")
            else:
                self.logger.warning("Failed to save to history")
        except Exception as e:
            self.logger.error(f"Error saving to history: {e}")
