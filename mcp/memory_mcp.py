import logging
from typing import Dict, Any, List
from cnst.memory_type import MemoryType


def extract_memory_data(result: Dict[str, Any], memory_type: MemoryType) -> List[Dict[str, Any]]:
    map_data = result.get("map", {})
    type_data = map_data.get(memory_type.value, {})
    return type_data.get("list", [])


class MemoryMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_memory_by_type(self, brand: str, types: List[MemoryType]) -> Dict[str, Any]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return {}

        try:
            type_values = [t.value for t in types]
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
            return extract_memory_data(result, MemoryType.CONVERSATION_HISTORY)
        except Exception as e:
            self.logger.error(f"Failed to fetch conversation history: {e}")
            return []

    async def get_listener_context(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.LISTENER_CONTEXT])
            return extract_memory_data(result, MemoryType.LISTENER_CONTEXT)
        except Exception as e:
            self.logger.error(f"Failed to fetch listener context: {e}")
            return []

    async def get_audience_context(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.AUDIENCE_CONTEXT])
            return extract_memory_data(result, MemoryType.AUDIENCE_CONTEXT)
        except Exception as e:
            self.logger.error(f"Failed to fetch audience context: {e}")
            return []

    async def get_instant_messages(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.INSTANT_MESSAGE])
            return extract_memory_data(result, MemoryType.INSTANT_MESSAGE)
        except Exception as e:
            self.logger.error(f"Failed to fetch instant messages: {e}")
            return []

    async def get_events(self, brand: str) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.EVENT])
            return extract_memory_data(result, MemoryType.EVENT)
        except Exception as e:
            self.logger.error(f"Failed to fetch events: {e}")
            return []