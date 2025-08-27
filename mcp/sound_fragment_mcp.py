import logging
from typing import Dict, Any

from cnst.play_list_item_type import PlaylistItemType
from mcp.mcp_client import MCPClient


class SoundFragmentMCP:
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_brand_sound_fragment(self, brand: str, fragment_type: str = PlaylistItemType.SONG.value) -> Dict[str, Any]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return {}

        try:
            params = {
                "brand": brand,
                "fragment_type": fragment_type
            }

            response_payload = await self.mcp_client.call_tool("get_brand_sound_fragment", params)

            if not response_payload:
                self.logger.error("Tool call returned empty payload. Check the mcp_client's logs for details.")
                return {}

            self.logger.info(f"Fetched sound fragment data for brand {brand}: {response_payload}")
            return response_payload

        except Exception as e:
            self.logger.error(f"An unexpected error occurred while fetching sound fragment: {e}")
            return {}
