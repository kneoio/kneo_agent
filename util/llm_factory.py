import asyncio
from typing import Dict

from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from openai import AsyncOpenAI

from cnst.llm_types import LlmType
from llm.langchain.langchain_adapter import LangChainAdapter
from llm.openai.openai_adapter import OpenAIAdapter
import logging


class LlmFactory:
    def __init__(self, config: Dict):
        self.config = config
        self.clients = {}
        self.llm_type = LlmType.GROQ
        self.logger = None
        self.moonshot_client = None
        self.deepseek_client = None
        self.openrouter_client = None
        moonshot_cfg = self.config.get('moonshot', {})
        if moonshot_cfg.get('api_key'):
            self.moonshot_client = AsyncOpenAI(
                api_key=moonshot_cfg.get('api_key'),
                base_url="https://api.moonshot.ai/v1"
            )
        deepseek_cfg = self.config.get('deepseek', {})
        if deepseek_cfg.get('api_key'):
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_cfg.get('api_key'),
                base_url="https://api.deepseek.com"
            )
        openrouter_cfg = self.config.get('openrouter', {})
        if openrouter_cfg.get('api_key'):
            headers = openrouter_cfg.get('headers') or {}
            self.openrouter_client = AsyncOpenAI(
                api_key=openrouter_cfg.get('api_key'),
                base_url=openrouter_cfg.get('base_url', "https://openrouter.ai/api/v1"),
                default_headers=headers if isinstance(headers, dict) else None
            )

    def get_llm_client(self, llm_type: LlmType, internet_mcp=None, enable_sound_fragment_tool=False):
        if not self.logger:
            self.logger = logging.getLogger(__name__)

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            loop_id = 0
        cache_key = f"{llm_type}_{internet_mcp is not None}_{enable_sound_fragment_tool}_{loop_id}"
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
            if internet_mcp:
                client.tool_functions["search_internet"] = internet_mcp.search_internet
            if enable_sound_fragment_tool:
                from tools.sound_fragment_tool import get_brand_sound_fragment
                client.tool_functions["get_brand_sound_fragment"] = get_brand_sound_fragment
            self.clients[cache_key] = client
            return client
        elif llm_type == LlmType.DEEPSEEK and self.deepseek_client:
            cfg = self.config.get('deepseek', {})
            model = cfg.get('model')
            temperature = cfg.get('temperature')
            client = OpenAIAdapter(self.deepseek_client, model=model, temperature=temperature)
            client.llm_type = llm_type
            if internet_mcp:
                client.tool_functions["search_internet"] = internet_mcp.search_internet
            if enable_sound_fragment_tool:
                from tools.sound_fragment_tool import get_brand_sound_fragment
                client.tool_functions["get_brand_sound_fragment"] = get_brand_sound_fragment
            self.clients[cache_key] = client
            return client
        elif llm_type == LlmType.OPENROUTER and self.openrouter_client:
            cfg = self.config.get('openrouter', {})
            model = cfg.get('model')
            temperature = cfg.get('temperature')
            client = OpenAIAdapter(self.openrouter_client, model=model, temperature=temperature)
            client.llm_type = llm_type
            if internet_mcp:
                client.tool_functions["search_internet"] = internet_mcp.search_internet
            if enable_sound_fragment_tool:
                from tools.sound_fragment_tool import get_brand_sound_fragment
                client.tool_functions["get_brand_sound_fragment"] = get_brand_sound_fragment
            self.clients[cache_key] = client
            return client

        if base_client is not None:
            client = LangChainAdapter(base_client)
            client.llm_type = llm_type

            if internet_mcp:
                client.bind_tool_function("search_internet", internet_mcp.search_internet)
            if enable_sound_fragment_tool:
                from tools.sound_fragment_tool import get_brand_sound_fragment
                client.bind_tool_function("get_brand_sound_fragment", get_brand_sound_fragment)
            if internet_mcp or enable_sound_fragment_tool:
                self.logger.info(f"LLM client ({llm_type.name}) initialized with tools enabled")
            else:
                self.logger.info(f"LLM client ({llm_type.name}) initialized without tools")

            self.clients[cache_key] = client
            return client

        return None
