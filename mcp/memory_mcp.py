import logging
from typing import Dict, Any, List
from cnst.memory_type import MemoryType


def extract_memory_data(result: Dict[str, Any], memory_type: MemoryType) -> List[Dict[str, Any]]:
    logger = logging.getLogger(__name__)
    logger.debug(f"extract_memory_data called with memory_type: {memory_type.value}")
    logger.debug(f"extract_memory_data result keys: {list(result.keys()) if result else 'None'}")

    map_data = result.get("map", {})
    logger.debug(f"map_data keys: {list(map_data.keys()) if map_data else 'None'}")

    type_data = map_data.get(memory_type.value, {})
    logger.debug(f"type_data for {memory_type.value}: {type_data}")

    extracted_list = type_data.get("list", [])
    logger.debug(f"extracted list length: {len(extracted_list)}")
    return extracted_list


class MemoryMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("MemoryMCP initialized")

    async def get_memory_by_type(self, brand: str, types: List[MemoryType]) -> Dict[str, Any]:
        self.logger.debug(f"get_memory_by_type called with brand: {brand}, types: {[t.name for t in types]}")

        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return {}

        try:
            type_values = [t.value for t in types]
            self.logger.info(f"Calling MCP tool with brand: {brand}, type_values: {type_values}")

            tool_params = {
                "brand": brand,
                "types": type_values
            }
            self.logger.debug(f"Tool parameters: {tool_params}")

            result = await self.mcp_client.call_tool("get_memory_by_type", tool_params)
            self.logger.debug(f"Raw MCP result type: {type(result)}")
            self.logger.debug(f"Raw MCP result: {result}")

            memory_data = result if isinstance(result, dict) else {}
            self.logger.info(f"Processed memory data keys: {list(memory_data.keys()) if memory_data else 'None'}")
            return memory_data

        except Exception as e:
            self.logger.error(f"Failed to fetch memory data - Exception type: {type(e).__name__}")
            self.logger.error(f"Failed to fetch memory data - Exception message: {str(e)}")
            self.logger.error(f"Failed to fetch memory data - Brand: {brand}, Types: {[t.value for t in types]}")
            import traceback
            self.logger.error(f"Failed to fetch memory data - Traceback: {traceback.format_exc()}")
            return {}

    async def get_conversation_history(self, brand: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_conversation_history called for brand: {brand}")

        if not self.mcp_client:
            self.logger.warning("get_conversation_history: No MCP client available")
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.CONVERSATION_HISTORY])
            self.logger.debug(f"get_conversation_history raw result: {result}")

            extracted_data = extract_memory_data(result, MemoryType.CONVERSATION_HISTORY)
            self.logger.info(f"get_conversation_history extracted {len(extracted_data)} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Failed to fetch conversation history: {e}")
            import traceback
            self.logger.error(f"get_conversation_history traceback: {traceback.format_exc()}")
            return []

    async def get_listener_context(self, brand: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_listener_context called for brand: {brand}")

        if not self.mcp_client:
            self.logger.warning("get_listener_context: No MCP client available")
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.LISTENER_CONTEXT])
            self.logger.debug(f"get_listener_context raw result: {result}")

            extracted_data = extract_memory_data(result, MemoryType.LISTENER_CONTEXT)
            self.logger.info(f"get_listener_context extracted {len(extracted_data)} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Failed to fetch listener context: {e}")
            import traceback
            self.logger.error(f"get_listener_context traceback: {traceback.format_exc()}")
            return []

    async def get_audience_context(self, brand: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_audience_context called for brand: {brand}")

        if not self.mcp_client:
            self.logger.warning("get_audience_context: No MCP client available")
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.AUDIENCE_CONTEXT])
            self.logger.debug(f"get_audience_context raw result: {result}")

            extracted_data = extract_memory_data(result, MemoryType.AUDIENCE_CONTEXT)
            self.logger.info(f"get_audience_context extracted {len(extracted_data)} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Failed to fetch audience context: {e}")
            import traceback
            self.logger.error(f"get_audience_context traceback: {traceback.format_exc()}")
            return []

    async def get_instant_messages(self, brand: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_instant_messages called for brand: {brand}")

        if not self.mcp_client:
            self.logger.warning("get_instant_messages: No MCP client available")
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.INSTANT_MESSAGE])
            self.logger.debug(f"get_instant_messages raw result: {result}")

            extracted_data = extract_memory_data(result, MemoryType.INSTANT_MESSAGE)
            self.logger.info(f"get_instant_messages extracted {len(extracted_data)} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Failed to fetch instant messages: {e}")
            import traceback
            self.logger.error(f"get_instant_messages traceback: {traceback.format_exc()}")
            return []

    async def get_events(self, brand: str) -> List[Dict[str, Any]]:
        self.logger.debug(f"get_events called for brand: {brand}")

        if not self.mcp_client:
            self.logger.warning("get_events: No MCP client available")
            return []

        try:
            result = await self.get_memory_by_type(brand, [MemoryType.EVENT])
            self.logger.debug(f"get_events raw result: {result}")

            extracted_data = extract_memory_data(result, MemoryType.EVENT)
            self.logger.info(f"get_events extracted {len(extracted_data)} items")
            return extracted_data

        except Exception as e:
            self.logger.error(f"Failed to fetch events: {e}")
            import traceback
            self.logger.error(f"get_events traceback: {traceback.format_exc()}")
            return []