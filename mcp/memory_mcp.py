import logging
from typing import Dict, Any, List

from cnst.memory_type import MemoryType


class MemoryMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_memory_by_type(self, brand: str, types: List[MemoryType]) -> Dict[str, Any]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return {}

        try:
            type_values = [t.name for t in types]
            result = await self.mcp_client.call_tool("get_memory_by_type", {
                "brand": brand,
                "types": type_values
            })
            memory_data = result if isinstance(result, dict) else {}
            self.logger.info(f"Fetched memory data for brand {brand}, types: {type_values}")
            return memory_data
        except Exception as e:
            self.logger.error(f"Failed to fetch memory data: {e}")
            return {}

    async def get_conversation_history(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.CONVERSATION_HISTORY])
            history = result.get(MemoryType.CONVERSATION_HISTORY.name, [])
            return history
        except Exception as e:
            self.logger.error(f"Failed to fetch conversation history: {e}")
            return []

    async def get_listener_context(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.LISTENER_CONTEXT])
            context = result.get(MemoryType.LISTENER_CONTEXT.name, [])
            return context
        except Exception as e:
            self.logger.error(f"Failed to fetch listener context: {e}")
            return []

    async def get_audience_context(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.AUDIENCE_CONTEXT])
            context = result.get(MemoryType.AUDIENCE_CONTEXT.name, [])
            return context
        except Exception as e:
            self.logger.error(f"Failed to fetch audience context: {e}")
            return []

    async def get_instant_messages(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.INSTANT_MESSAGE])
            messages = result.get(MemoryType.INSTANT_MESSAGE.name, [])
            return messages
        except Exception as e:
            self.logger.error(f"Failed to fetch instant messages: {e}")
            return []

    async def get_events(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.EVENT])
            events = result.get(MemoryType.EVENT.name, [])
            return events
        except Exception as e:
            self.logger.error(f"Failed to fetch events: {e}")
            return []