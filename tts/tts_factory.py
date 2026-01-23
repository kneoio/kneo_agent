import logging
from typing import Dict, Any

from tts.tts_engine import TTSEngine
from tts.elevenlabs_engine import ElevenLabsTTSEngine
from tts.gcp_engine import GCPTTSEngine
from tts.modelslab_engine import ModelsLabTTSEngine


class TTSEngineFactory:
    _logger = logging.getLogger(__name__)

    @staticmethod
    def create_engine(tts_engine_type: str, config: Dict[str, Any]) -> TTSEngine:
        if not tts_engine_type:
            TTSEngineFactory._logger.error("ttsEngineType is missing or empty")
            raise ValueError("ttsEngineType is required and cannot be empty")

        engine_type_lower = tts_engine_type.lower()

        if engine_type_lower == "elevenlabs":
            elevenlabs_config = config.get("elevenlabs")
            if not elevenlabs_config:
                TTSEngineFactory._logger.error("elevenlabs configuration is missing in config")
                raise ValueError("elevenlabs configuration is required for ElevenLabs TTS engine")
            
            api_key = elevenlabs_config.get("api_key")
            if not api_key:
                TTSEngineFactory._logger.error("elevenlabs.api_key is missing in config")
                raise ValueError("elevenlabs.api_key is required for ElevenLabs TTS engine")
            
            TTSEngineFactory._logger.info("Creating ElevenLabs TTS engine")
            return ElevenLabsTTSEngine(api_key=api_key)

        elif engine_type_lower == "google":
            google_tts_config = config.get("google_tts")
            if not google_tts_config:
                TTSEngineFactory._logger.error("google_tts configuration is missing in config")
                raise ValueError("google_tts configuration is required for GCP TTS engine")
            
            credentials_path = google_tts_config.get("credentials_path")
            if not credentials_path:
                TTSEngineFactory._logger.error("google_tts.credentials_path is missing in config")
                raise ValueError("google_tts.credentials_path is required for GCP TTS engine")
            
            TTSEngineFactory._logger.info("Creating GCP TTS engine")
            return GCPTTSEngine(credentials_path=credentials_path)

        elif engine_type_lower == "modelslab":
            modelslab_config = config.get("modelslab")
            if not modelslab_config:
                TTSEngineFactory._logger.error("modelslab configuration is missing in config")
                raise ValueError("modelslab configuration is required for ModelsLab TTS engine")
            
            api_key = modelslab_config.get("api_key")
            if not api_key:
                TTSEngineFactory._logger.error("modelslab.api_key is missing in config")
                raise ValueError("modelslab.api_key is required for ModelsLab TTS engine")
            
            TTSEngineFactory._logger.info("Creating ModelsLab TTS engine")
            return ModelsLabTTSEngine(api_key=api_key)

        else:
            TTSEngineFactory._logger.error(f"Unknown TTS engine type: {tts_engine_type}")
            raise ValueError(f"Unknown TTS engine type: {tts_engine_type}. Supported types: elevenlabs, google, modelslab")
