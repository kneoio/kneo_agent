import logging
from typing import Dict, Any, List, Optional


class QueueMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_queue(self, brand: str) -> Dict[str, Any]:
        result = await self.mcp_client.call_tool("get_queue", {
            "brand": brand
        })
        self.logger.info(f"Fetched queue data for brand {brand}")
        return result

    async def add_to_queue(self, brand_name: str, sound_fragment_uuid: Optional[str] = None,
                          file_path: Optional[str] = None, priority: Optional[int] = None) -> Dict[str, Any]:
        result = await self.mcp_client.call_tool("add_to_queue", {
            "brandName": brand_name,
            "soundFragmentUUID": sound_fragment_uuid,
            "filePath": file_path,
            "priority": priority
        })
        self.logger.info(f"Added to queue for brand {brand_name}: {result.get('success', False)}")
        return result