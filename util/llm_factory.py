from typing import Dict

from cnst.llm_types import LlmType
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq


class LlmFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.clients = {}

    def getLlmClient(self, llmType: LlmType):
        if llmType is None:
            return None
        if llmType in self.clients:
            return self.clients[llmType]
        client = None
        if llmType == LlmType.CLAUDE:
            cfg = self.config.get('claude')
            client = ChatAnthropic(
                model_name=cfg.get('model'),
                temperature=cfg.get('temperature'),
                api_key=cfg.get('api_key')
            )
        elif llmType == LlmType.GROQ:
            cfg = self.config.get('groq')
            client = ChatGroq(
                model_name=cfg.get('model'),
                temperature=cfg.get('temperature'),
                api_key=cfg.get('api_key')
            )
        if client is not None:
            self.clients[llmType] = client
        return client
