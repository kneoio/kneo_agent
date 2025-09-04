import logging
from typing import Dict, Any, Optional, Tuple

from elevenlabs.client import ElevenLabs

from api.interaction_memory import InteractionMemory
from core.prerecorded import Prerecorded


class AudioProcessor:
    def __init__(self, elevenlabs_inst: ElevenLabs, prerecorded: Prerecorded,
                 agent_config: Dict[str, Any], memory: InteractionMemory):
        self.elevenlabs_inst = elevenlabs_inst
        self.prerecorded = prerecorded
        self.agent_config = agent_config
        self.memory = memory
        self.logger = logging.getLogger(__name__)

    async def generate_tts_audio(self, text: str, title: str, artist: str) -> Tuple[Optional[bytes], str]:
        if not text:
            return None, "No text provided for TTS"

        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return await self.prerecorded.get_prerecorded_audio()

        try:
            self._save_to_history(title, artist, text)

            voice_id = self.agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')
            audio_stream = self.elevenlabs_inst.text_to_speech.convert(
                voice_id=voice_id,
                text=text[:500],
                #model_id="eleven_multilingual_v2",
                model_id="eleven_v3",
                #output_format="mp3_44100_128"
                output_format="mp3_44100_192"
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
