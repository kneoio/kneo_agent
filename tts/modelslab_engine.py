import logging
from typing import Optional, Tuple

from tts.tts_engine import TTSEngine


class ModelsLabTTSEngine(TTSEngine):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ModelsLab API key is required")
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    async def generate_speech(self, text: str, voice_id: str, language_code: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        self.logger.error("ModelsLab TTS engine is not yet implemented")
        return None, "ModelsLab TTS engine is not yet implemented"
