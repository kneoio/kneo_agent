import json
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

    async def generate_tts_audio(self, text: str) -> Tuple[Optional[bytes], str]:
        if not text:
            return None, "No text provided for TTS"

        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            audio_data, message, _ = await self.prerecorded.get_prerecorded_audio()
            return audio_data, message

        try:
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

    async def generate_tts_dialogue(self, dialogue_json: str) -> Tuple[Optional[bytes], str]:
        try:
            dialogue = json.loads(dialogue_json)
            audio_stream = self.elevenlabs_inst.text_to_dialogue.convert(inputs=dialogue)
            audio_data = b"".join(audio_stream)
            if audio_data:
                self.logger.info("Dialogue TTS generation successful")
                return audio_data, "Generated multi-voice dialogue"
            return None, "Dialogue TTS produced no data"
        except Exception as e:
            self.logger.error(f"Dialogue TTS failed: {e}")
            return None, f"Dialogue TTS failed: {str(e)}"
