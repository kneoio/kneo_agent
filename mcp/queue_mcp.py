import logging
from typing import Optional


class QueueMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def add_to_queue(self, brand_name: str, sound_fragment_uuid: Optional[str] = None,
                          file_path: Optional[str] = None, priority: Optional[int] = None) -> bool:
        result = await self.mcp_client.call_tool("add_to_queue", {
            "brand": brand_name,
            "songIds": {"song1": sound_fragment_uuid},
            "filePaths": {"audio1": file_path} if file_path else {},
            "mergingMethod": "INTRO_PLUS_SONG",
            "priority": priority
        })
        self.logger.info(f"Added to queue for brand {brand_name}: {result}")
        return result