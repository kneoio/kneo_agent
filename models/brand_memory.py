from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict
from uuid import UUID


@dataclass
class BrandMemory:
    id: UUID
    last_mod_date: datetime
    brand: str
    day: date
    summary: Dict[str, Any]
