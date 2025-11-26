from dataclasses import dataclass
from typing import Any


@dataclass
class AppState:
    db: Any = None
    brand_memory: Any = None
    user_memory: Any = None
    summarizer: Any = None
    listener_api: Any = None
    stations_api: Any = None
    audio_processor: Any = None
    conversation_summarizer: Any = None
    summarizer_task: Any = None
