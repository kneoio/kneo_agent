import json
from typing import Dict, Callable

from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from openai import AsyncOpenAI
import openai

from cnst.llm_types import LlmType
from mcp.external.internet_mcp import InternetMCP


class ToolEnabledLLMClient:
    def __init__(self, base_client):
        self.base_client = base_client
        self.tool_functions = {}
        self.llm_type = None

    def bind_tool_function(self, name: str, func: Callable):
        self.tool_functions[name] = func

    async def ainvoke(self, messages, tools=None):
        if not tools:
            return await self.base_client.ainvoke(messages)

        bound_client = self.base_client.bind_tools(tools)
        response = await bound_client.ainvoke(messages)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_messages = [response]

            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name') or tool_call.get('function', {}).get('name')

                if tool_name in self.tool_functions:
                    try:
                        args = tool_call.get('args') or json.loads(tool_call.get('function', {}).get('arguments', '{}'))

                        result = await self.tool_functions[tool_name](**args)

                        tool_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get('id'),
                            "name": tool_name,
                            "content": json.dumps(result)
                        })
                    except Exception as e:
                        tool_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get('id'),
                            "content": f"Error: {str(e)}"
                        })

            final_response = await bound_client.ainvoke(messages + tool_messages)
            return final_response

        return response


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

        cache_key = f"{llm_type}_{internet_mcp is not None}"
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
            client = OpenAICompatClient(self.moonshot_client, model=model, temperature=temperature)
            client.llm_type = llm_type
            self.clients[cache_key] = client
            return client

        if base_client is not None:
            client = ToolEnabledLLMClient(base_client)
            client.llm_type = llm_type

            if internet_mcp:
                client.bind_tool_function("search_internet", internet_mcp.search_internet)
                self.logger.info(f"LLM client ({llm_type.name}) initialized with internet_mcp tools enabled")
            else:
                self.logger.info(f"LLM client ({llm_type.name}) initialized without internet tools")

            self.clients[cache_key] = client
            return client

        return None


class OpenAICompatClient:
    def __init__(self, openai_client: AsyncOpenAI, model: str, temperature=None):
        self.client = openai_client
        self.model = model
        self.temperature = temperature
        self.tool_functions = {}
        self.llm_type = None

    async def ainvoke(self, messages, tools=None):
        openai_messages = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            openai_messages.append({"role": role, "content": content})
        kwargs = {"model": self.model, "messages": openai_messages}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            resp = await self.client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content if resp and resp.choices else ""
            return {"content": text}
        except openai.RateLimitError as e:
            return {"content": f"Rate limited by provider: {str(e)}"}
        except Exception as e:
            return {"content": f"Provider error: {str(e)}"}


async def generate_dj_intro_text(llm_client, prompt, dj_name, context, brand, events, title, artist, genres, history,
                                 listeners, instant_message):
    tools = [InternetMCP.get_tool_definition(default_engine="Perplexity")]

    formatted_messages = ""
    if instant_message:
        formatted_messages = "; ".join([
            f"{msg.get('from', 'Anonymous')}: {msg.get('content', '')}"
            for msg in instant_message
        ])

    song_prompt = prompt.format(
        ai_dj_name=dj_name,
        context=context,
        brand=brand,
        events=events,
        title=title,
        artist=artist,
        genres=genres,
        history=history,
        listeners=listeners,
        messages=formatted_messages
    )

    messages = [
        {"role": "system", "content": "Generate plain text"},
        {"role": "user", "content": song_prompt}
    ]
    return await llm_client.ainvoke(messages=messages, tools=tools)