import json
from typing import Dict, Callable

from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq

from cnst.llm_types import LlmType
from mcp.external.internet_mcp import InternetMCP


class ToolEnabledLLMClient:
    def __init__(self, base_client):
        self.base_client = base_client
        self.tool_functions = {}

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

    def get_llm_client(self, llm_type: LlmType, internet_mcp=None):
        self.llm_type = llm_type

        cache_key = f"{llm_type}_{internet_mcp is not None}"
        if cache_key in self.clients:
            return self.clients[cache_key]

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

        if base_client is not None:
            client = ToolEnabledLLMClient(base_client)

            if internet_mcp:
                client.bind_tool_function("search_internet", internet_mcp.search_internet)

            self.clients[cache_key] = client
            return client

        return None


async def generate_dj_intro_text(llm_client, prompt, dj_name, context, brand, events, title, artist, genres, history,
                                 listeners, instant_message):
    tools = [InternetMCP.get_tool_definition()]

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