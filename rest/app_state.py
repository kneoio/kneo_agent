from dataclasses import dataclass
from typing import Any


@dataclass
class AppState:
    db: Any = None
    brand_memory: Any = None
    user_memory: Any = None
    summarizer: Any = None
