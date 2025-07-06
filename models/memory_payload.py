# models/memory_payload.py

import json
from typing import Dict

class MemoryPayload:
    def __init__(self, data: Dict):
        self.memory_type = data.get('memoryType')
        self.content = data.get('content', {})
    
    def get_content_as_json(self) -> str:
        return json.dumps(self.content)
    
    def is_valid(self) -> bool:
        return self.memory_type is not None and self.content
