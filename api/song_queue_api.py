#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from api.client import APIClient

class SongQueueAPI:
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.api_client = APIClient()  # Will use environment variables automatically

    def get_available_songs(self, query=None, genre=None, limit=20) -> List[Dict[str, Any]]:
        params = {"limit": limit}
        if query:
            params["query"] = query
        if genre:
            params["genre"] = genre

        response = self.api_client.get("songs/available", params)
        if response:
            return response.get("songs", [])
        return []

    def get_queue(self) -> List[Dict[str, Any]]:
        response = self.api_client.get("queue")
        if response:
            return response.get("queue", [])
        return []

    def add_song(self, song_id: str, position: int = None) -> bool:
        data = {"song_id": song_id}
        if position is not None:
            data["position"] = position

        response = self.api_client.post("queue/add", data)
        if response and response.get("success"):
            self.logger.info(f"Added song to queue: {song_id}")
            return True
        return False

    def remove_song(self, position: int) -> bool:
        response = self.api_client.delete(f"queue/remove", {"position": position})
        if response and response.get("success"):
            self.logger.info(f"Removed song from queue at position {position}")
            return True
        return False

    def clear_queue(self) -> bool:
        response = self.api_client.delete("queue/clear")
        if response and response.get("success"):
            self.logger.info("Cleared song queue")
            return True
        return False

    def play_next(self) -> Optional[Dict[str, Any]]:
        response = self.api_client.post("queue/play_next", {})
        if response and response.get("success"):
            song = response.get("song")
            if song:
                self.logger.info(f"Now playing: {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
            return song
        return None

    def previous_song(self) -> Optional[Dict[str, Any]]:
        response = self.api_client.post("queue/play_previous", {})
        if response and response.get("success"):
            song = response.get("song")
            if song:
                self.logger.info(
                    f"Playing previous song: {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
            return song
        return None

    def get_current_song(self) -> Optional[Dict[str, Any]]:
        response = self.api_client.get("queue/current")
        if response:
            return response.get("song")
        return None

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        params = {}
        if limit:
            params["limit"] = limit

        response = self.api_client.get("queue/history", params)
        if response:
            return response.get("history", [])
        return []