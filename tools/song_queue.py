#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from tools.base_tool import BaseTool
from api.song_queue_api import SongQueueAPI


class SongQueueManager(BaseTool):
    def _initialize(self):
        self.api = SongQueueAPI(self.config)

    def _get_name(self) -> str:
        return "song_queue_manager"

    def _get_description(self) -> str:
        return "Manages the song queue, including adding, removing, and playing songs."

    def _get_category(self) -> str:
        return "music"

    def get_capabilities(self) -> List[str]:
        return [
            "add_song",
            "remove_song",
            "get_queue",
            "clear_queue",
            "play_next",
            "previous_song",
            "get_current_song",
            "get_history",
            "get_available_songs"
        ]

    def get_available_songs(self, query=None, genre=None, limit=20) -> List[Dict[str, Any]]:
        songs = self.api.get_available_songs(query, genre, limit)
        return songs

    def add_song(self, song: Dict[str, Any], position: int = None) -> bool:
        song_id = song.get("id")
        if not song_id:
            self.logger.error("Cannot add song: missing song ID")
            return False

        return self.api.add_song(song_id, position)

    def remove_song(self, position: int) -> bool:
        return self.api.remove_song(position)

    def get_queue(self) -> List[Dict[str, Any]]:
        return self.api.get_queue()

    def clear_queue(self) -> bool:
        return self.api.clear_queue()

    def play_next(self) -> Optional[Dict[str, Any]]:
        return self.api.play_next()

    def previous_song(self) -> Optional[Dict[str, Any]]:
        return self.api.previous_song()

    def get_current_song(self) -> Optional[Dict[str, Any]]:
        return self.api.get_current_song()

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        return self.api.get_history(limit)