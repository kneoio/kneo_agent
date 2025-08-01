import logging
from typing import Dict, Any, List


class SoundFragmentMCP:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_song_by_mood(self, brand: str, mood: str) -> Dict[str, Any]:
        try:
            songs = await self.get_by_type(brand, types="SONG")
            if not songs:
                return {}

            mood_songs = []
            for song in songs:
                song_info = song.get('soundfragment', {})
                song_mood = song_info.get('mood', '').lower()
                if mood.lower() in song_mood or song_mood in mood.lower():
                    mood_songs.append(song)

            import random
            if mood_songs:
                return random.choice(mood_songs)
            return songs[0] if songs else {}

        except Exception as e:
            self.logger.error(f"Failed to get song by mood: {e}")
            return {}

    async def get_by_type(self, brand: str, page: int = 1, size: int = 50,
                          genres: str = None, sources: str = None, types: str = None) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return []

        try:
            params = {
                "brand": brand,
                "page": page,
                "size": size
            }

            if genres:
                params["genres"] = genres
            if sources:
                params["sources"] = sources
            if types:
                params["types"] = types

            result = await self.mcp_client.call_tool("get_brand_sound_fragments", params)
            songs = result.get("fragments", [])
            self.logger.info(f"Fetched {len(songs)} songs for brand {brand}")
            return songs
        except Exception as e:
            self.logger.error(f"Failed to fetch songs: {e}")
            return []

    async def search_songs(self, query: str, page: int = 1, size: int = 50,
                           genres: str = None, sources: str = None, types: str = None) -> List[Dict[str, Any]]:
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return []

        try:
            params = {
                "query": query,
                "page": page,
                "size": size
            }

            if genres:
                params["genres"] = genres
            if sources:
                params["sources"] = sources
            if types:
                params["types"] = types

            result = await self.mcp_client.call_tool("search_sound_fragments", params)
            songs = result.get("fragments", [])
            self.logger.info(f"Found {len(songs)} songs for query '{query}'")
            return songs
        except Exception as e:
            self.logger.error(f"Failed to search songs: {e}")
            return []

    async def get_song_details(self, song_id: str) -> Dict[str, Any]:
        if not self.mcp_client:
            return {"error": "No MCP client"}

        try:
            result = await self.mcp_client.call_tool("get_song", {"song_id": song_id})
            return {"details": result.content[0].text}
        except Exception as e:
            return {"error": str(e)}