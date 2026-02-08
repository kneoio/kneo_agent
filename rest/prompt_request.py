from pydantic import BaseModel
from cnst.llm_types import LlmType


class PromptRequest(BaseModel):
    prompt: str
    draft: str
    llm: LlmType
