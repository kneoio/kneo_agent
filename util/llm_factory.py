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

    def get_llm_client(self, llm_type: LlmType, internet_mcp=None, enable_sound_fragment_tool=False, enable_listener_tool=False, enable_stations_tools=False, enable_queue_tool=False):
        if not self.logger:
            self.logger = logging.getLogger(__name__)

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            loop_id = 0
        cache_key = f"{llm_type}_{internet_mcp is not None}_{enable_sound_fragment_tool}_{enable_listener_tool}_{enable_stations_tools}_{enable_queue_tool}_{loop_id}"
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
            cfg = self.config.get('groq', {})
            base_client = ChatGroq(
                model=cfg.get('model'),
                temperature=cfg.get('temperature'),
                groq_api_key=cfg.get('api_key')
            )
            
        elif llm_type == LlmType.GOOGLE:
            # Use the official google-generativeai library directly to avoid
            # incompatibilities with the langchain_google_genai wrapper.
            import google.generativeai as genai
            cfg = self.config.get('google', {})
            if not cfg:
                self.logger.error('Google config missing')
                raise ValueError('Missing google config')
            api_key = cfg.get('api_key')
            model_name = cfg.get('model')
            temperature = cfg.get('temperature', 0.0)
            # Configure the library (global config)
            genai.configure(api_key=api_key)
            # Create a simple adapter that matches the LangChainAdapter interface
            class _GoogleAdapter:
                def __init__(self, model, temperature):
                    self.model = model
                    self.temperature = temperature
                    self.llm_type = None
                    self.tool_functions = {}
                
                def bind_tool_function(self, name: str, func):
                    self.tool_functions[name] = func
                
                def _convert_messages_to_prompt(self, messages):
                    parts = []
                    for msg in messages:
                        role = msg.get("role")
                        content = msg.get("content")
                        if not content:
                            continue
                        if role == "system":
                            parts.append(f"System: {content}")
                        elif role == "assistant":
                            parts.append(f"Assistant: {content}")
                        elif role == "user":
                            parts.append(f"User: {content}")
                    return "\n\n".join(parts)
                
                async def invoke(self, messages, tools=None):
                    prompt = self._convert_messages_to_prompt(messages)
                    return await self.ainvoke(prompt, tools)
                
                async def ainvoke(self, prompt: str, tools=None):
                    generation_config = genai.GenerationConfig(temperature=self.temperature)
                    import asyncio
                    response = await asyncio.to_thread(self.model.generate_content, prompt, generation_config=generation_config)
                    class _Resp:
                        def __init__(self, content):
                            self.content = content
                    return _Resp(response.text)
            base_client = _GoogleAdapter(genai.GenerativeModel(model_name), temperature)

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
            if enable_queue_tool:
                from tools.queue_tool import queue_intro_and_song
                client.tool_functions["queue_intro_and_song"] = queue_intro_and_song
            if enable_listener_tool:
                pass
            if enable_stations_tools:
                pass
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
            if enable_queue_tool:
                from tools.queue_tool import queue_intro_and_song
                client.tool_functions["queue_intro_and_song"] = queue_intro_and_song
            if enable_listener_tool:
                pass
            if enable_stations_tools:
                pass
            self.clients[cache_key] = client
            return client

        if base_client is not None:
            # For Google we already have a compatible adapter, so return it directly
            if llm_type == LlmType.GOOGLE:
                client = base_client
            else:
                client = LangChainAdapter(base_client)
            client.llm_type = llm_type

            if internet_mcp:
                client.bind_tool_function("search_internet", internet_mcp.search_internet)
            if enable_sound_fragment_tool:
                from tools.sound_fragment_tool import get_brand_sound_fragment
                client.bind_tool_function("get_brand_sound_fragment", get_brand_sound_fragment)
            if enable_queue_tool:
                from tools.queue_tool import queue_intro_and_song
                client.bind_tool_function("queue_intro_and_song", queue_intro_and_song)
            if enable_listener_tool:
                pass
            if enable_stations_tools:
                pass
            if internet_mcp or enable_sound_fragment_tool or enable_listener_tool or enable_stations_tools or enable_queue_tool:
                self.logger.info(f"LLM client ({llm_type.name}) initialized with tools enabled")
            else:
                self.logger.info(f"LLM client ({llm_type.name}) initialized without tools")

            self.clients[cache_key] = client
            return client

        return None
