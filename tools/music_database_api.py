#!/usr/bin/env python3
# tools/music_database_api.py - Simplified Music Database API

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools.base_tool import BaseTool


class MusicDatabaseAPI(BaseTool):
    """Tool for accessing music data with built-in mock data."""

    def _initialize(self):
        """Initialize the Music Database with mock data."""
        self.logger = logging.getLogger(__name__)
        self.songs = self._get_mock_songs()
        self.artists = self._get_mock_artists()
        self.genres = self._get_mock_genres()
        self.playlists = self._get_mock_playlists()
        self.playlist_songs = {
            1: [1, 2, 6, 7, 8, 11, 12, 13, 14, 18, 19],  # Pop Hits
            2: [1, 3, 4, 5, 17],  # Classic Rock
            3: [7, 8, 9, 10, 11, 12, 14, 18, 19, 20]  # Recent Hits
        }
        self.logger.info("Initialized Music Database API with mock data")

    def _get_name(self) -> str:
        """Get the name of the tool."""
        return "music_database"

    def _get_description(self) -> str:
        """Get a description of the tool."""
        return "Provides access to the music database for searching and retrieving songs."

    def _get_category(self) -> str:
        """Get the category of the tool."""
        return "music"

    def get_capabilities(self) -> List[str]:
        """Get a list of capabilities provided by this tool."""
        return [
            "search_songs",
            "get_song_by_id",
            "add_song",
            "update_song",
            "delete_song",
            "get_genres",
            "get_artists",
            "get_playlists",
            "create_playlist",
            "add_to_playlist",
            "remove_from_playlist"
        ]

    def search_songs(self, criteria: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for songs based on various criteria."""
        results = self.songs.copy()

        # Apply filters based on criteria
        for key, value in criteria.items():
            if key == "title" and value:
                results = [s for s in results if value.lower() in s["title"].lower()]
            elif key == "artist" and value:
                results = [s for s in results if value.lower() in s["artist"].lower()]
            elif key == "album" and value:
                results = [s for s in results if s.get("album") and value.lower() in s["album"].lower()]
            elif key == "genre" and value:
                results = [s for s in results if s.get("genre") and value.lower() in s["genre"].lower()]
            elif key == "min_year" and value:
                results = [s for s in results if s.get("release_year", 0) >= int(value)]
            elif key == "max_year" and value:
                results = [s for s in results if s.get("release_year", 9999) <= int(value)]

        # Sort and limit results
        results.sort(key=lambda x: x["title"])
        return results[:limit]

    def get_song_by_id(self, song_id: int) -> Optional[Dict[str, Any]]:
        """Get a song by its ID."""
        for song in self.songs:
            if song["id"] == song_id:
                return song.copy()
        return None

    def add_song(self, song_info: Dict[str, Any]) -> Optional[int]:
        """Add a new song to the database."""
        # Generate a new ID
        new_id = max([s["id"] for s in self.songs]) + 1

        # Create the new song
        new_song = {
            "id": new_id,
            "title": song_info.get("title", "Unknown"),
            "artist": song_info.get("artist", "Unknown"),
            "album": song_info.get("album"),
            "genre": song_info.get("genre"),
            "duration": song_info.get("duration", 0),
            "release_year": song_info.get("release_year")
        }

        self.songs.append(new_song)
        self.logger.info(f"Added song: {new_song['title']} by {new_song['artist']}")
        return new_id

    def update_song(self, song_id: int, song_info: Dict[str, Any]) -> bool:
        """Update an existing song."""
        for i, song in enumerate(self.songs):
            if song["id"] == song_id:
                # Update the song
                for key, value in song_info.items():
                    self.songs[i][key] = value

                self.logger.info(f"Updated song with ID {song_id}")
                return True

        return False

    def delete_song(self, song_id: int) -> bool:
        """Delete a song from the database."""
        for i, song in enumerate(self.songs):
            if song["id"] == song_id:
                del self.songs[i]
                self.logger.info(f"Deleted song with ID {song_id}")
                return True

        return False

    def get_genres(self) -> List[Dict[str, Any]]:
        """Get all available genres."""
        return self.genres.copy()

    def get_artists(self) -> List[Dict[str, Any]]:
        """Get all available artists."""
        return self.artists.copy()

    def get_playlists(self) -> List[Dict[str, Any]]:
        """Get all available playlists."""
        result = []
        for playlist in self.playlists:
            playlist_copy = playlist.copy()
            playlist_copy["song_count"] = len(self.playlist_songs.get(playlist["id"], []))
            result.append(playlist_copy)

        return result

    def create_playlist(self, name: str, description: str = None) -> Optional[int]:
        """Create a new playlist."""
        # Generate a new ID
        new_id = max([p["id"] for p in self.playlists]) + 1

        # Create the new playlist
        new_playlist = {
            "id": new_id,
            "name": name,
            "description": description
        }

        self.playlists.append(new_playlist)
        self.playlist_songs[new_id] = []
        self.logger.info(f"Created playlist: {name}")
        return new_id

    def add_to_playlist(self, playlist_id: int, song_id: int, position: int = None) -> bool:
        """Add a song to a playlist."""
        # Check if playlist and song exist
        if playlist_id not in [p["id"] for p in self.playlists] or song_id not in [s["id"] for s in self.songs]:
            return False

        # Initialize playlist songs list if needed
        if playlist_id not in self.playlist_songs:
            self.playlist_songs[playlist_id] = []

        # Add song to playlist
        if song_id not in self.playlist_songs[playlist_id]:
            if position is not None and 0 <= position < len(self.playlist_songs[playlist_id]):
                self.playlist_songs[playlist_id].insert(position, song_id)
            else:
                self.playlist_songs[playlist_id].append(song_id)

            self.logger.info(f"Added song {song_id} to playlist {playlist_id}")
            return True
        else:
            return False

    def remove_from_playlist(self, playlist_id: int, song_id: int) -> bool:
        """Remove a song from a playlist."""
        if playlist_id in self.playlist_songs and song_id in self.playlist_songs[playlist_id]:
            self.playlist_songs[playlist_id].remove(song_id)
            self.logger.info(f"Removed song {song_id} from playlist {playlist_id}")
            return True
        else:
            return False

    def _get_mock_songs(self) -> List[Dict[str, Any]]:
        """Get mock song data."""
        return [
            {
                "id": 1, "title": "Bohemian Rhapsody", "artist": "Queen",
                "album": "A Night at the Opera", "genre": "Rock", "duration": 354, "release_year": 1975
            },
            {
                "id": 2, "title": "Billie Jean", "artist": "Michael Jackson",
                "album": "Thriller", "genre": "Pop", "duration": 294, "release_year": 1983
            },
            {
                "id": 3, "title": "Hotel California", "artist": "Eagles",
                "album": "Hotel California", "genre": "Rock", "duration": 390, "release_year": 1976
            },
            {
                "id": 4, "title": "Sweet Child O' Mine", "artist": "Guns N' Roses",
                "album": "Appetite for Destruction", "genre": "Rock", "duration": 356, "release_year": 1987
            },
            {
                "id": 5, "title": "Imagine", "artist": "John Lennon",
                "album": "Imagine", "genre": "Rock", "duration": 183, "release_year": 1971
            },
            {
                "id": 6, "title": "Thriller", "artist": "Michael Jackson",
                "album": "Thriller", "genre": "Pop", "duration": 357, "release_year": 1982
            },
            {
                "id": 7, "title": "Uptown Funk", "artist": "Mark Ronson ft. Bruno Mars",
                "album": "Uptown Special", "genre": "Pop", "duration": 270, "release_year": 2014
            },
            {
                "id": 8, "title": "Shape of You", "artist": "Ed Sheeran",
                "album": "÷", "genre": "Pop", "duration": 233, "release_year": 2017
            },
            {
                "id": 9, "title": "Despacito", "artist": "Luis Fonsi ft. Daddy Yankee",
                "album": "Vida", "genre": "Reggaeton", "duration": 229, "release_year": 2017
            },
            {
                "id": 10, "title": "Blinding Lights", "artist": "The Weeknd",
                "album": "After Hours", "genre": "Synthwave", "duration": 200, "release_year": 2019
            },
            {
                "id": 11, "title": "Dance Monkey", "artist": "Tones and I",
                "album": "The Kids Are Coming", "genre": "Pop", "duration": 210, "release_year": 2019
            },
            {
                "id": 12, "title": "Bad Guy", "artist": "Billie Eilish",
                "album": "When We All Fall Asleep, Where Do We Go?", "genre": "Pop", "duration": 194,
                "release_year": 2019
            },
            {
                "id": 13, "title": "Happy", "artist": "Pharrell Williams",
                "album": "G I R L", "genre": "Pop", "duration": 232, "release_year": 2013
            },
            {
                "id": 14, "title": "Havana", "artist": "Camila Cabello ft. Young Thug",
                "album": "Camila", "genre": "Pop", "duration": 217, "release_year": 2017
            },
            {
                "id": 15, "title": "Someone Like You", "artist": "Adele",
                "album": "21", "genre": "Pop", "duration": 285, "release_year": 2011
            },
            {
                "id": 16, "title": "Believer", "artist": "Imagine Dragons",
                "album": "Evolve", "genre": "Rock", "duration": 204, "release_year": 2017
            },
            {
                "id": 17, "title": "Stairway to Heaven", "artist": "Led Zeppelin",
                "album": "Led Zeppelin IV", "genre": "Rock", "duration": 482, "release_year": 1971
            },
            {
                "id": 18, "title": "Can't Stop the Feeling!", "artist": "Justin Timberlake",
                "album": "Trolls (Original Motion Picture Soundtrack)", "genre": "Pop", "duration": 236,
                "release_year": 2016
            },
            {
                "id": 19, "title": "Watermelon Sugar", "artist": "Harry Styles",
                "album": "Fine Line", "genre": "Pop", "duration": 174, "release_year": 2019
            },
            {
                "id": 20, "title": "Dynamite", "artist": "BTS",
                "album": "BE", "genre": "K-pop", "duration": 199, "release_year": 2020
            }
        ]

    def _get_mock_artists(self) -> List[Dict[str, Any]]:
        """Get mock artist data."""
        return [
            {"id": 1, "name": "Queen"},
            {"id": 2, "name": "Michael Jackson"},
            {"id": 3, "name": "Eagles"},
            {"id": 4, "name": "Guns N' Roses"},
            {"id": 5, "name": "John Lennon"},
            {"id": 6, "name": "Mark Ronson ft. Bruno Mars"},
            {"id": 7, "name": "Ed Sheeran"},
            {"id": 8, "name": "Luis Fonsi ft. Daddy Yankee"},
            {"id": 9, "name": "The Weeknd"},
            {"id": 10, "name": "Tones and I"}
        ]

    def _get_mock_genres(self) -> List[Dict[str, Any]]:
        """Get mock genre data."""
        return [
            {"id": 1, "name": "Rock"},
            {"id": 2, "name": "Pop"},
            {"id": 3, "name": "Reggaeton"},
            {"id": 4, "name": "Synthwave"},
            {"id": 5, "name": "K-pop"}
        ]

    def _get_mock_playlists(self) -> List[Dict[str, Any]]:
        """Get mock playlist data."""
        return [
            {"id": 1, "name": "Pop Hits", "description": "Collection of popular pop songs"},
            {"id": 2, "name": "Classic Rock", "description": "Timeless rock classics"},
            {"id": 3, "name": "Recent Hits", "description": "Songs from the last few years"}
        ]