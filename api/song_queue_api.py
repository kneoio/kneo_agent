#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from api.client import APIClient
from models.song import Song


class SongQueueAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = APIClient()  # Will use environment variables automatically

    def get_available_songs(self, query=None, genre=None, limit=20, brand_id=None) -> List[Song]:
        """Get available songs, filtered by brand if specified."""
        params = {"limit": limit}
        if query:
            params["query"] = query
        if genre:
            params["genre"] = genre

        # Use the brand endpoint if a brand_id is provided
        endpoint = "available-soundfragments"
        if brand_id:
            # Using the slug name format as specified in the endpoint
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.get(endpoint, params)
        songs = []

        if response:
            # Convert raw data to Song objects
            for song_data in response:  # Direct array response
                songs.append(Song.from_dict(song_data))

        return songs

    def get_queue(self, brand_id=None) -> List[Song]:
        """Get the current song queue for a specific brand."""
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
        """Add a song to the queue for a specific brand."""
        endpoint = "queue/add"
        data = {"song_id": song_id}

        if position is not None:
            data["position"] = position

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.post(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Added song to queue: {song_id} for brand: {brand_id}")
            return True
        return False

    def remove_song(self, position: int, brand_id=None) -> bool:
        """Remove a song from the queue for a specific brand."""
        endpoint = "queue/remove"
        data = {"position": position}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.delete(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Removed song from queue at position {position} for brand: {brand_id}")
            return True
        return False

    def clear_queue(self, brand_id=None) -> bool:
        """Clear the song queue for a specific brand."""
        endpoint = "queue/clear"
        data = {}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.delete(endpoint, data)
        if response and response.get("success"):
            self.logger.info(f"Cleared song queue for brand: {brand_id}")
            return True
        return False

    def play_next(self, brand_id=None) -> Optional[Song]:
        """Play the next song in the queue for a specific brand."""
        endpoint = "queue/play_next"
        data = {}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.post(endpoint, data)
        if response and response.get("success"):
            song_data = response.get("song")
            if song_data:
                song = Song.from_dict(song_data)
                self.logger.info(f"Now playing: {song.title} by {song.artist} for brand: {brand_id}")
                return song
        return None

    def previous_song(self, brand_id=None) -> Optional[Song]:
        """Play the previous song in the queue for a specific brand."""
        endpoint = "queue/play_previous"
        data = {}

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.post(endpoint, data)
        if response and response.get("success"):
            song_data = response.get("song")
            if song_data:
                song = Song.from_dict(song_data)
                self.logger.info(f"Playing previous song: {song.title} by {song.artist} for brand: {brand_id}")
                return song
        return None

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

    def get_history(self, limit: int = None, brand_id=None) -> List[Song]:
        """Get the play history for a specific brand."""
        endpoint = "queue/history"
        params = {}

        if limit:
            params["limit"] = limit

        if brand_id:
            endpoint = f"{endpoint}?brand={brand_id}"

        response = self.api_client.get(endpoint, params)
        songs = []

        if response:
            for song_data in response.get("history", []):
                songs.append(Song.from_dict(song_data))

        return songs