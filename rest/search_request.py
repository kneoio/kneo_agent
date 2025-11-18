from pydantic import BaseModel
from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine

class SearchRequest(BaseModel):
    prompt: str
    llm: LlmType
    searchEngine: SearchEngine = SearchEngine.Brave
