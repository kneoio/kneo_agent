#!/usr/bin/env python3
import logging
from typing import Dict, Any, List, Optional
from tools.base_tool import BaseTool
from api.song_queue_api import SongQueueAPI
from models.song import Song


class SongQueueManager(BaseTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.api = SongQueueAPI(self.config)

    @property
    def name(self) -> str:
        return "song_queue_manager"

    @property
    def description(self) -> str:
        return "Manages the song queue, including adding, removing, and playing songs."

    @property
    def category(self) -> str:
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

    def get_available_songs(self, query=None, genre=None, limit=20, brand_id=None) -> List[Dict[str, Any]]:
        # Apply brand profile constraints if available
        brand = self.brand_manager.get_brand(brand_id)

        if brand and brand.profile:
            # If no genre specified but profile has allowed genres, use the first allowed genre
            if not genre and brand.profile.allowedGenres:
                genre = brand.profile.allowedGenres[0]

            # If genre specified but not allowed, replace with allowed genre
            if genre and brand.profile.allowedGenres and genre not in brand.profile.allowedGenres:
                self.logger.warning(
                    f"Genre {genre} not allowed for brand {brand_id}. Using {brand.profile.allowedGenres[0]} instead.")
                genre = brand.profile.allowedGenres[0]

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Call API with possibly modified parameters
        songs = self.api.get_available_songs(query, genre, limit, brand_slug)

        # Convert Song objects to dictionaries for uniform handling
        song_dicts = []
        for song in songs:
            if isinstance(song, Song):
                song_dicts.append(song.to_dict())
            elif isinstance(song, dict):
                song_dicts.append(song)

        # Filter explicit content if needed
        if brand and brand.profile and not brand.profile.explicitContent:
            song_dicts = [song for song in song_dicts if not song.get("explicit", False)]

        return song_dicts

    def add_song(self, song, position: int = None, brand_id=None) -> bool:
        """Add a song to the queue for a specific brand."""
        # Convert to dictionary if it's a Song object
        if isinstance(song, Song):
            song_dict = song.to_dict()
            song_id = song.id
        else:
            # It's already a dictionary or some other object
            song_dict = song if isinstance(song, dict) else {"id": getattr(song, "id", None)}
            song_id = song_dict.get("id")

        if not song_id:
            self.logger.error("Cannot add song: missing song ID")
            return False

        # Get brand context
        brand = self.brand_manager.get_brand(brand_id)

        # Check if song meets brand profile constraints
        if brand and brand.profile:
            # Check genre constraints
            song_genre = song_dict.get("genre")
            if song_genre and brand.profile.allowedGenres and song_genre not in brand.profile.allowedGenres:
                self.logger.warning(f"Song genre {song_genre} not allowed for brand {brand_id}")
                return False

            # Check explicit content constraints
            if not brand.profile.explicitContent and song_dict.get("explicit", False):
                self.logger.warning(f"Explicit content not allowed for brand {brand_id}")
                return False

        # Track the song in brand state
        if brand:
            queue = brand.get_state_value("song_queue") or []
            queue.append(song_dict)
            brand.update_state("song_queue", queue)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        return self.api.add_song(song_id, position, brand_slug)

    def remove_song(self, position: int, brand_id=None) -> bool:
        # Update brand state if available
        brand = self.brand_manager.get_brand(brand_id)
        if brand:
            queue = brand.get_state_value("song_queue") or []
            if 0 <= position < len(queue):
                queue.pop(position)
                brand.update_state("song_queue", queue)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        return self.api.remove_song(position, brand_slug)

    def get_queue(self, brand_id=None) -> List[Dict[str, Any]]:
        # Get brand for slug name
        brand = self.brand_manager.get_brand(brand_id)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Get API queue (external state)
        api_queue = self.api.get_queue(brand_slug)

        # Convert Song objects to dictionaries
        queue_dicts = []
        for song in api_queue:
            if isinstance(song, Song):
                queue_dicts.append(song.to_dict())
            elif isinstance(song, dict):
                queue_dicts.append(song)

        # Update brand state (internal state) with latest queue
        if brand:
            brand.update_state("song_queue", queue_dicts)

        return queue_dicts

    def clear_queue(self, brand_id=None) -> bool:
        # Get brand for slug name and state update
        brand = self.brand_manager.get_brand(brand_id)

        # Clear brand state queue if available
        if brand:
            brand.update_state("song_queue", [])

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        return self.api.clear_queue(brand_slug)

    def play_next(self, brand_id=None) -> Optional[Dict[str, Any]]:
        # Get brand for slug name and state update
        brand = self.brand_manager.get_brand(brand_id)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Get next song from API
        next_song = self.api.play_next(brand_slug)

        # Convert to dictionary if it's a Song object
        if isinstance(next_song, Song):
            next_song_dict = next_song.to_dict()
        else:
            next_song_dict = next_song

        # Update brand state with currently playing song
        if brand and next_song_dict:
            brand.update_state("current_song", next_song_dict)

        return next_song_dict

    def previous_song(self, brand_id=None) -> Optional[Dict[str, Any]]:
        # Get brand for slug name and state update
        brand = self.brand_manager.get_brand(brand_id)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Get previous song from API
        prev_song = self.api.previous_song(brand_slug)

        # Convert to dictionary if it's a Song object
        if isinstance(prev_song, Song):
            prev_song_dict = prev_song.to_dict()
        else:
            prev_song_dict = prev_song

        # Update brand state with currently playing song
        if brand and prev_song_dict:
            brand.update_state("current_song", prev_song_dict)

        return prev_song_dict

    def get_current_song(self, brand_id=None) -> Optional[Dict[str, Any]]:
        # Get brand for slug name and state update
        brand = self.brand_manager.get_brand(brand_id)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Get current song from API
        current_song = self.api.get_current_song(brand_slug)

        # Convert to dictionary if it's a Song object
        if isinstance(current_song, Song):
            current_song_dict = current_song.to_dict()
        else:
            current_song_dict = current_song

        # Update brand state
        if brand and current_song_dict:
            brand.update_state("current_song", current_song_dict)

        return current_song_dict

    def get_history(self, limit: int = None, brand_id=None) -> List[Dict[str, Any]]:
        # Get brand for slug name and state update
        brand = self.brand_manager.get_brand(brand_id)

        # Get the slug name for API requests
        brand_slug = brand.slugName if brand else brand_id

        # Get API history
        history = self.api.get_history(limit, brand_slug)

        # Convert Song objects to dictionaries
        history_dicts = []
        for song in history:
            if isinstance(song, Song):
                history_dicts.append(song.to_dict())
            elif isinstance(song, dict):
                history_dicts.append(song)

        # Track history in brand state
        if brand:
            brand.update_state("song_history", history_dicts)

        return history_dicts