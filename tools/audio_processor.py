import json
import logging
from typing import Optional, Tuple
from elevenlabs.client import ElevenLabs

from api.interaction_memory import InteractionMemory
from models.live_container import LiveRadioStation


class AudioProcessor:
    def __init__(self, elevenlabs_inst: ElevenLabs, station: LiveRadioStation, memory: InteractionMemory):
        self.elevenlabs_inst = elevenlabs_inst
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

        try:
            voice_id = self.station.tts.preferredVoice
            audio_stream = self.elevenlabs_inst.text_to_speech.convert(
                voice_id=voice_id,
                text=text[:1000],
                # model_id="eleven_multilingual_v2",
                model_id="eleven_v3",
                # output_format="mp3_44100_128"
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
        dialogue = ""
        try:
            dialogue = json.loads(dialogue_json)
            settings = {"volume_normalization": "on"}
            audio_stream = self.elevenlabs_inst.text_to_dialogue.convert(inputs=dialogue, settings=settings)
            audio_data = b"".join(audio_stream)
            if audio_data:
                self.logger.info("Dialogue TTS generation successful")
                return audio_data, "Generated multi-voice dialogue"
            return None, "Dialogue TTS produced no data"
        except Exception as e:
            self.logger.error(f"Dialogue TTS failed: {e}")
            self.logger.error(f"Dialogue: {dialogue}")
            return None, f"Dialogue TTS failed: {str(e)}"
