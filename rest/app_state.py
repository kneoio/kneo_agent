from dataclasses import dataclass
from typing import Any


@dataclass
class AppState:
    db: Any = None
    user_memory: Any = None
    summarizer: Any = None
    listener_api: Any = None
    stations_api: Any = None
    audio_processor: Any = None
