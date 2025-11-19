from typing import Optional
from pydantic import BaseModel
from cnst.llm_types import LlmType


class ChatRequest(BaseModel):
    text: str
    brand: Optional[str] = None
    llm: LlmType = LlmType.OPENROUTER
    chat_id: int
    name: Optional[str] = None
