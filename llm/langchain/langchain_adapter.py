from typing import Callable

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


class LangChainAdapter:
    def __init__(self, base_client):
        self.base_client = base_client
        self.tool_functions = {}
        self.llm_type = None

    def bind_tool_function(self, name: str, func: Callable):
        self.tool_functions[name] = func

    def _convert_messages(self, messages):
        lc_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    lc_messages.append(AIMessage(content=content, tool_calls=tool_calls))
                else:
                    lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id"),
                    name=msg.get("name")
                ))
        return lc_messages

    async def invoke(self, messages, tools=None):
        lc_messages = self._convert_messages(messages)
        if tools:
            bound_client = self.base_client.bind_tools(tools)
            return await bound_client.ainvoke(lc_messages)
        return await self.base_client.ainvoke(lc_messages)

    async def ainvoke(self, prompt: str, tools=None):
        """Convenient async call for a simple prompt.

        Args:
            prompt: The user prompt string.
            tools: Optional list of tool definitions to bind.
        Returns:
            The response from the underlying LangChain client.
        """
        # Convert the plain string prompt into the message format expected by ``invoke``.
        messages = [{"role": "user", "content": prompt}]
        return await self.invoke(messages, tools)
