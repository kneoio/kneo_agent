import json
from typing import Callable


class LangChainAdapter:
    def __init__(self, base_client):
        self.base_client = base_client
        self.tool_functions = {}
        self.llm_type = None

    def bind_tool_function(self, name: str, func: Callable):
        self.tool_functions[name] = func

    async def invoke(self, messages, tools=None):
        if tools:
            bound_client = self.base_client.bind_tools(tools)
            return await bound_client.ainvoke(messages)
        return await self.base_client.ainvoke(messages)
