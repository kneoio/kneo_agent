import asyncio
from typing import Dict

from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from openai import AsyncOpenAI

from cnst.llm_types import LlmType
from llm.langchain.langchain_adapter import LangChainAdapter
from llm.openai.openai_adapter import OpenAIAdapter


class LlmFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.clients = {}
        self.llm_type = LlmType.GROQ
        self.logger = None
        self.moonshot_client = None
        moonshot_cfg = self.config.get('moonshot', {})
        if moonshot_cfg.get('api_key'):
            self.moonshot_client = AsyncOpenAI(
                api_key=moonshot_cfg.get('api_key'),
                base_url="https://api.moonshot.ai/v1"
            )

    def get_llm_client(self, llm_type: LlmType, internet_mcp=None):
        if not self.logger:
            import logging
            self.logger = logging.getLogger(__name__)

        self.llm_type = llm_type

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            loop_id = 0
        cache_key = f"{llm_type}_{internet_mcp is not None}_{loop_id}"
        if cache_key in self.clients:
            client = self.clients[cache_key]
            client.llm_type = llm_type
            return client

        base_client = None
        if llm_type == LlmType.CLAUDE:
            cfg = self.config.get('claude')
            base_client = ChatAnthropic(
                model_name=cfg.get('model'),
                temperature=cfg.get('temperature'),
                api_key=cfg.get('api_key')
            )
        elif llm_type == LlmType.GROQ:
            cfg = self.config.get('groq')
            base_client = ChatGroq(
                model=cfg.get('model'),
                temperature=cfg.get('temperature'),
                api_key=cfg.get('api_key')
            )
        elif llm_type == LlmType.KIMI and self.moonshot_client:
            cfg = self.config.get('moonshot', {})
            model = cfg.get('model')
            temperature = cfg.get('temperature')
            client = OpenAIAdapter(self.moonshot_client, model=model, temperature=temperature)
            client.llm_type = llm_type
            self.clients[cache_key] = client
            return client

        if base_client is not None:
            client = LangChainAdapter(base_client)
            client.llm_type = llm_type

            if internet_mcp:
                client.bind_tool_function("search_internet", internet_mcp.search_internet)
                self.logger.info(f"LLM client ({llm_type.name}) initialized with internet_mcp tools enabled")
            else:
                self.logger.info(f"LLM client ({llm_type.name}) initialized without internet tools")

            self.clients[cache_key] = client
            return client

        return None
