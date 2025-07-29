import logging
from typing import Dict, Any, List


class SoundfragmentMCP:
    """Handles music catalog operations via MCP"""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_songs(self, brand: str, page: int = 1, size: int = 50) -> List[Dict[str, Any]]:
        """Fetch songs from MCP catalog"""
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return []

        try:
            result = await self.mcp_client.call_tool("get_brand_soundfragments", {
                "brand": brand,
                "page": page,
                "size": size
            })
            songs = result.get("fragments", [])
            self.logger.info(f"Fetched {len(songs)} songs for brand {brand}")
            return songs
        except Exception as e:
            self.logger.error(f"Failed to fetch songs: {e}")
            return []

    async def get_song_details(self, song_id: str) -> Dict[str, Any]:
        """Get detailed song information"""
        if not self.mcp_client:
            return {"error": "No MCP client"}

        try:
            result = await self.mcp_client.call_tool("get_song", {"song_id": song_id})
            return {"details": result.content[0].text}
        except Exception as e:
            return {"error": str(e)}
