from abc import ABC, abstractmethod
from typing import Optional, Tuple


class TTSEngine(ABC):
    @abstractmethod
    async def generate_speech(self, text: str, voice_id: str, language_code: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        pass

    async def generate_dialogue(self, dialogue_json: str) -> Tuple[Optional[bytes], str]:
        return None, "Dialogue generation not supported by this TTS engine"
