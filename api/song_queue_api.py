import logging
from typing import Dict, Any, List, Optional
from api.broadcaster_client import BroadcasterAPIClient
from models.song import Song


class SongQueueAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = BroadcasterAPIClient(config)

    def get_available_songs(self, limit=20, brand_id=None) -> List[Song]:
        params = {"limit": limit}
        endpoint = "available-soundfragments"
        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.get(endpoint, params)
        songs = []

        if response:
            for song_data in response:
                songs.append(Song.from_dict(song_data))

        return songs

    def get_queue(self, brand_id=None) -> List[Song]:
        endpoint = "queue"
        params = {}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.get(endpoint, params)
        songs = []

        if response:
            for song_data in response.get("queue", []):
                songs.append(Song.from_dict(song_data))

        return songs

    def add_song(self, song_id: str, position: int = None, brand_id=None) -> bool:
        endpoint = "queue/add"
        data = {"song_id": song_id}

        if position is not None:
            data["position"] = position

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"
        self.logger.info(f"Requested to add song: (ID: {song_id})")
        response = self.api_client.post(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Added song to queue: {song_id} for brand: {brand_id}")
            return True
        return False

    def get_current_song(self, brand_id=None) -> Optional[Song]:
        """Get the currently playing song for a specific brand."""
        endpoint = "queue/current"
        params = {}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.get(endpoint, params)
        if response and response.get("song"):
            return Song.from_dict(response.get("song"))
        return None