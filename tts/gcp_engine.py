import logging
import os
from typing import Optional, Tuple

from google.cloud import texttospeech_v1
from google.cloud.texttospeech_v1.types import VoiceSelectionParams, AudioConfig, SynthesisInput

from tts.tts_engine import TTSEngine


class GCPTTSEngine(TTSEngine):
    def __init__(self, credentials_path: str):
        if not credentials_path:
            raise ValueError("GCP TTS credentials_path is required")
        
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"GCP TTS credentials file not found: {credentials_path}")
        
        self.client = texttospeech_v1.TextToSpeechClient.from_service_account_json(credentials_path)
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
        else:
            self.logger.info(f"TTS text length: {len(text)} chars")

        try:
            lang_code = language_code or "en-US"
            
            voice_params = {
                "language_code": lang_code,
                "name": voice_id,
            }
            
            if "gemini" in voice_id.lower() or ("chirp" in voice_id.lower() and "hd" in voice_id.lower()):
                voice_params["model_name"] = "gemini-2.5-flash-tts"
            elif not any(sep in voice_id for sep in ["-", "_"]):
                voice_params["model_name"] = "gemini-2.5-flash-tts"
            
            model_info = f" model={voice_params.get('model_name', 'standard')}" if "model_name" in voice_params else ""
            self.logger.info(f"GCP TTS using voice={voice_id}{model_info} lang={lang_code}")
            
            voice = VoiceSelectionParams(voice_params)

            audio_config = AudioConfig({
                "audio_encoding": 2,
            })

            synthesis_input = SynthesisInput({"text": text[:1000]})

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            if response.audio_content:
                self.logger.info("GCP TTS generation successful")
                return response.audio_content, f"Generated TTS using voice: {voice_id}"
            else:
                return None, "GCP TTS conversion resulted in empty audio"

        except Exception as e:
            self.logger.error(f"GCP TTS generation failed: {e}")
            return None, f"GCP TTS generation failed: {str(e)}"
