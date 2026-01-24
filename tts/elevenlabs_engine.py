import json
import logging
from typing import Optional, Tuple

from elevenlabs.client import ElevenLabs

from tts.tts_engine import TTSEngine


class ElevenLabsTTSEngine(TTSEngine):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ElevenLabs API key is required")
        self.client = ElevenLabs(api_key=api_key)
        self.logger = logging.getLogger(__name__)

    async def generate_speech(self, text: str, voice_id: str, language_code: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        if not text:
            return None, "No text provided for TTS"

        if not voice_id:
            self.logger.error("Missing voice_id for TTS generation")
            return None, "Missing voice_id for TTS generation"

        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return None, "TTS conversion resulted in empty audio due to copyright content"

        if len(text) > 980:
            self.logger.warning(f"TTS text length approaching limit: {len(text)} chars")

        try:
            normalized_lang_code = None
            if language_code:
                if "-" in language_code:
                    normalized_lang_code = language_code.split("-")[0]
                else:
                    normalized_lang_code = language_code
            
            self.logger.info(f"ElevenLabs TTS using voice={voice_id} lang={normalized_lang_code}")
            
            audio_stream = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text[:1000],
                model_id="eleven_v3",
                output_format="mp3_44100_192",
                language_code=normalized_lang_code
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

    async def generate_dialogue(self, dialogue_json: str) -> Tuple[Optional[bytes], str]:
        if not dialogue_json or dialogue_json.strip() == "":
            self.logger.error("Dialogue TTS failed: empty or None input from LLM")
            return None, "Dialogue TTS failed: LLM returned no dialogue content"

        try:
            dialogue = json.loads(dialogue_json)
        except Exception as e:
            self.logger.error(f"Dialogue TTS parse failed: {e}")
            self.logger.error(f"Dialogue raw: {dialogue_json[:500]}")
            return None, f"Dialogue TTS failed: {str(e)}"

        settings = {"volume_normalization": "on"}
        try:
            audio_stream = self.client.text_to_dialogue.convert(inputs=dialogue, settings=settings)
            audio_data = b"".join(audio_stream)
            if audio_data:
                self.logger.info("Dialogue TTS generation successful")
                return audio_data, "Generated multi-voice dialogue"
            return None, "Dialogue TTS produced no data"
        except Exception as e:
            self.logger.error(f"Dialogue TTS failed: {e}")
            self.logger.error(f"Dialogue: {dialogue}")
            return None, f"Dialogue TTS failed: {str(e)}"
