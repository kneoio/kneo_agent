import json
from datetime import datetime, UTC

from llm.noise_filter import NoiseFilter


class BrandMemoryManager:
    def __init__(self):
        self.memory = {}
        self.filter = NoiseFilter()

    @staticmethod
    def _normalize(text: str) -> str:
        if not text:
            return ""
        t = text.strip()
        if t.startswith("[") and t.endswith("]"):
            try:
                arr = json.loads(t)
                lines = []
                for item in arr:
                    msg = item.get("text", "").strip()
                    if msg:
                        lines.append(msg)
                return "\n".join(lines)
            except Exception:
                return t
        return t

    def add(self, brand: str, text: str):

        if self.filter.is_noise(text):
            return

        cleaned = self._normalize(text)
        if not cleaned.strip():
            return
        entry = {
            "t": datetime.now(UTC).isoformat(timespec="seconds"),
            "text": cleaned
        }
        m = self.memory.setdefault(brand, [])
        m.append(entry)
        if len(m) > 20:
            m[:] = m[-20:]

    def get(self, brand: str):
        return self.memory.get(brand, [])

    def clear(self, brand: str):
        self.memory.pop(brand, None)

    def clear_all(self):
        self.memory.clear()
