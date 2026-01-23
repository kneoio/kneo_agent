import logging
from typing import Optional, Tuple

from models.live_container import LiveRadioStation
from tts.tts_engine import TTSEngine


class AudioProcessor:
    def __init__(self, tts_engine: TTSEngine, station: LiveRadioStation, memory):
        self.tts_engine = tts_engine
        self.station = station
        self.memory = memory
        self.logger = logging.getLogger(__name__)

    async def generate_tts_audio(self, text: str) -> Tuple[Optional[bytes], str]:
        if not text:
            return None, "No text provided for TTS"

        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return None, "TTS conversion resulted in empty audio due to copyright content"

        if len(text) > 980:
            self.logger.warning(f"TTS text length approaching limit: {len(text)} chars")
        else:
            self.logger.info(f"TTS text length -------> : {len(text)} chars")

        self.logger.info(f"TTS language_code: {self.station.languageTag}")

        try:
            voice_id = (self.station.tts.primaryVoice or "").strip()
            if not voice_id:
                self.logger.error("Missing primaryVoice for TTS generation")
                return None, "Missing primaryVoice for TTS generation"
            
            return await self.tts_engine.generate_speech(
                text=text,
                voice_id=voice_id,
                language_code=self.station.languageTag
            )

        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}")
            return None, f"TTS generation failed: {str(e)}"

    async def generate_tts_simple(self, text: str, voice_id: str) -> Tuple[Optional[bytes], str]:
        if not text:
            return None, "No text provided for TTS"
        
        if not voice_id:
            return None, "No voice_id provided for TTS"

        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return None, "TTS conversion resulted in empty audio due to copyright content"

        try:
            return await self.tts_engine.generate_speech(
                text=text,
                voice_id=voice_id,
                language_code=None
            )

        except Exception as e:
            self.logger.error(f"Simple TTS generation failed: {e}")
            return None, f"TTS generation failed: {str(e)}"

    async def generate_tts_dialogue(self, dialogue_json: str) -> Tuple[Optional[bytes], str]:
        if not dialogue_json or dialogue_json.strip() == "":
            self.logger.error("Dialogue TTS failed: empty or None input from LLM")
            return None, "Dialogue TTS failed: LLM returned no dialogue content"

        try:
            return await self.tts_engine.generate_dialogue(dialogue_json)
        except Exception as e:
            self.logger.error(f"Dialogue TTS failed: {e}")
            return None, f"Dialogue TTS failed: {str(e)}"
