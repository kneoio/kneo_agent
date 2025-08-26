import logging
from typing import Dict, Any, List

from cnst.play_list_item_type import PlaylistItemType


class SoundFragmentMCP:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_sound_fragment(self, brand: str, fragment_type: str = PlaylistItemType.SONG.value) ->  Dict[str, Any]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return {}

        try:
            params = {
                "brand": brand,
                "fragment_type": fragment_type
            }

            result = await self.mcp_client.call_tool("get_brand_sound_fragment", params)
            print(result)
            self.logger.info(f"Fetched {result} songs for brand {brand}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to fetch songs: {e}")
            return {}
