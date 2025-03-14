#!/usr/bin/env python3
# tools/music_database.py - Music Database tool

import logging
import json
import os
from typing import Dict, Any, List, Optional
import sqlite3
from pathlib import Path

from tools.base_tool import BaseTool


class MusicDatabase(BaseTool):
    """Tool for accessing and managing the music database."""

    def _initialize(self):
        """Initialize the Music Database."""
        self.db_path = self.config.get("db_path", "data/music.db")
        self.create_if_missing = self.config.get("create_if_missing", True)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Check if database exists, create if needed
        db_exists = os.path.exists(self.db_path)
        if not db_exists and not self.create_if_missing:
            self.logger.error(f"Database file not found: {self.db_path}")
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        # Connect to database and create tables if needed
        self.conn = self._connect_to_db()
        if not db_exists and self.create_if_missing:
            self._create_tables()

        self.logger.info(f"Connected to music database at {self.db_path}")

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

    def _connect_to_db(self) -> sqlite3.Connection:
        """
        Connect to the SQLite database.

        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return results as dictionaries
        return conn

    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Create songs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT,
            genre TEXT,
            duration INTEGER NOT NULL,
            release_year INTEGER,
            file_path TEXT,
            mood TEXT,
            energy_level TEXT,
            dance_type TEXT,
            tempo INTEGER,
            explicit BOOLEAN DEFAULT 0,
            language TEXT DEFAULT 'English',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create artists table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS artists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create genres table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create playlists table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create playlist_songs junction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_songs (
            playlist_id INTEGER,
            song_id INTEGER,
            position INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (playlist_id, song_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
        )
        ''')

        # Create mood_collections table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create mood_collection_songs junction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_collection_songs (
            collection_id INTEGER,
            song_id INTEGER,
            PRIMARY KEY (collection_id, song_id),
            FOREIGN KEY (collection_id) REFERENCES mood_collections(id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
        )
        ''')

        # Commit the changes
        self.conn.commit()
        self.logger.info("Created database tables")

    def search_songs(self, criteria: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for songs based on various criteria.

        Args:
            criteria: Dictionary of search criteria
            limit: Maximum number of results to return

        Returns:
            List of matching songs
        """
        cursor = self.conn.cursor()

        # Build the query based on criteria
        query = "SELECT * FROM songs WHERE 1=1"
        params = []

        # Add criteria to the query
        if "title" in criteria:
            query += " AND title LIKE ?"
            params.append(f"%{criteria['title']}%")

        if "artist" in criteria:
            query += " AND artist LIKE ?"
            params.append(f"%{criteria['artist']}%")

        if "album" in criteria:
            query += " AND album LIKE ?"
            params.append(f"%{criteria['album']}%")

        if "genre" in criteria:
            query += " AND genre LIKE ?"
            params.append(f"%{criteria['genre']}%")

        if "mood" in criteria:
            query += " AND mood LIKE ?"
            params.append(f"%{criteria['mood']}%")

        if "energy_level" in criteria:
            query += " AND energy_level = ?"
            params.append(criteria['energy_level'])

        if "dance_type" in criteria:
            query += " AND dance_type = ?"
            params.append(criteria['dance_type'])

        if "min_tempo" in criteria:
            query += " AND tempo >= ?"
            params.append(criteria['min_tempo'])

        if "max_tempo" in criteria:
            query += " AND tempo <= ?"
            params.append(criteria['max_tempo'])

        if "min_year" in criteria:
            query += " AND release_year >= ?"
            params.append(criteria['min_year'])

        if "max_year" in criteria:
            query += " AND release_year <= ?"
            params.append(criteria['max_year'])

        if "language" in criteria:
            query += " AND language = ?"
            params.append(criteria['language'])

        if "explicit" in criteria:
            query += " AND explicit = ?"
            params.append(1 if criteria['explicit'] else 0)

        # Add order by clause if specified
        if "order_by" in criteria:
            order_field = criteria["order_by"]
            order_dir = criteria.get("order_dir", "ASC").upper()
            if order_dir not in ["ASC", "DESC"]:
                order_dir = "ASC"

            valid_fields = ["title", "artist", "album", "genre", "duration", "release_year", "tempo"]
            if order_field in valid_fields:
                query += f" ORDER BY {order_field} {order_dir}"
            else:
                query += " ORDER BY title ASC"
        else:
            query += " ORDER BY title ASC"

        # Add limit
        query += f" LIMIT {limit}"

        # Execute the query
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]

        self.logger.debug(f"Song search found {len(results)} results for criteria: {criteria}")
        return results

    def get_song_by_id(self, song_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a song by its ID.

        Args:
            song_id: ID of the song to retrieve

        Returns:
            Song information or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)

        self.logger.warning(f"Song with ID {song_id} not found")
        return None

    def add_song(self, song_info: Dict[str, Any]) -> Optional[int]:
        """
        Add a new song to the database.

        Args:
            song_info: Dictionary containing song information

        Returns:
            ID of the added song or None if unsuccessful
        """
        # Validate required fields
        required_fields = ["title", "artist", "duration"]
        for field in required_fields:
            if field not in song_info:
                self.logger.error(f"Cannot add song: missing required field '{field}'")
                return None

        cursor = self.conn.cursor()

        # Prepare the query
        fields = []
        placeholders = []
        values = []

        for key, value in song_info.items():
            if key != "id":  # Skip the ID field
                fields.append(key)
                placeholders.append("?")
                values.append(value)

        query = f"INSERT INTO songs ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"

        try:
            cursor.execute(query, values)
            self.conn.commit()
            song_id = cursor.lastrowid
            self.logger.info(f"Added song: {song_info['title']} by {song_info['artist']} (ID: {song_id})")
            return song_id
        except Exception as e:
            self.logger.error(f"Failed to add song: {e}")
            self.conn.rollback()
            return None

    def update_song(self, song_id: int, song_info: Dict[str, Any]) -> bool:
        """
        Update an existing song.

        Args:
            song_id: ID of the song to update
            song_info: Dictionary containing updated song information

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        # Check if song exists
        cursor.execute("SELECT id FROM songs WHERE id = ?", (song_id,))
        if not cursor.fetchone():
            self.logger.error(f"Cannot update song: song with ID {song_id} not found")
            return False

        # Prepare the query
        set_clauses = []
        values = []

        for key, value in song_info.items():
            if key != "id":  # Skip the ID field
                set_clauses.append(f"{key} = ?")
                values.append(value)

        # Add updated_at timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE songs SET {', '.join(set_clauses)} WHERE id = ?"
        values.append(song_id)

        try:
            cursor.execute(query, values)
            self.conn.commit()
            self.logger.info(f"Updated song with ID {song_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update song: {e}")
            self.conn.rollback()
            return False

    def delete_song(self, song_id: int) -> bool:
        """
        Delete a song from the database.

        Args:
            song_id: ID of the song to delete

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("DELETE FROM songs WHERE id = ?", (song_id,))
            self.conn.commit()

            if cursor.rowcount > 0:
                self.logger.info(f"Deleted song with ID {song_id}")
                return True
            else:
                self.logger.warning(f"Song with ID {song_id} not found, nothing to delete")
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete song: {e}")
            self.conn.rollback()
            return False

    def get_genres(self) -> List[Dict[str, Any]]:
        """
        Get all available genres.

        Returns:
            List of genres
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM genres ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_artists(self) -> List[Dict[str, Any]]:
        """
        Get all available artists.

        Returns:
            List of artists
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM artists ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def get_playlists(self) -> List[Dict[str, Any]]:
        """
        Get all available playlists.

        Returns:
            List of playlists
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM playlists ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def create_playlist(self, name: str, description: str = None) -> Optional[int]:
        """
        Create a new playlist.

        Args:
            name: Name of the playlist
            description: Optional description of the playlist

        Returns:
            ID of the created playlist or None if unsuccessful
        """
        cursor = self.conn.cursor()

        try:
            if description:
                cursor.execute(
                    "INSERT INTO playlists (name, description) VALUES (?, ?)",
                    (name, description)
                )
            else:
                cursor.execute(
                    "INSERT INTO playlists (name) VALUES (?)",
                    (name,)
                )

            self.conn.commit()
            playlist_id = cursor.lastrowid
            self.logger.info(f"Created playlist: {name} (ID: {playlist_id})")
            return playlist_id
        except Exception as e:
            self.logger.error(f"Failed to create playlist: {e}")
            self.conn.rollback()
            return None

    def add_to_playlist(self, playlist_id: int, song_id: int, position: int = None) -> bool:
        """
        Add a song to a playlist.

        Args:
            playlist_id: ID of the playlist
            song_id: ID of the song to add
            position: Optional position in the playlist

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        # Check if playlist exists
        cursor.execute("SELECT id FROM playlists WHERE id = ?", (playlist_id,))
        if not cursor.fetchone():
            self.logger.error(f"Cannot add to playlist: playlist with ID {playlist_id} not found")
            return False

        # Check if song exists
        cursor.execute("SELECT id FROM songs WHERE id = ?", (song_id,))
        if not cursor.fetchone():
            self.logger.error(f"Cannot add to playlist: song with ID {song_id} not found")
            return False

        # Get the maximum position if none provided
        if position is None:
            cursor.execute(
                "SELECT MAX(position) FROM playlist_songs WHERE playlist_id = ?",
                (playlist_id,)
            )
            max_position = cursor.fetchone()[0]
            position = 1 if max_position is None else max_position + 1

        try:
            # Check if song is already in the playlist
            cursor.execute(
                "SELECT 1 FROM playlist_songs WHERE playlist_id = ? AND song_id = ?",
                (playlist_id, song_id)
            )

            if cursor.fetchone():
                # Update position if song is already in the playlist
                cursor.execute(
                    "UPDATE playlist_songs SET position = ? WHERE playlist_id = ? AND song_id = ?",
                    (position, playlist_id, song_id)
                )
            else:
                # Add song to playlist
                cursor.execute(
                    "INSERT INTO playlist_songs (playlist_id, song_id, position) VALUES (?, ?, ?)",
                    (playlist_id, song_id, position)
                )

            # Update playlist updated_at timestamp
            cursor.execute(
                "UPDATE playlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (playlist_id,)
            )

            self.conn.commit()
            self.logger.info(f"Added song {song_id} to playlist {playlist_id} at position {position}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add song to playlist: {e}")
            self.conn.rollback()
            return False

    def remove_from_playlist(self, playlist_id: int, song_id: int) -> bool:
        """
        Remove a song from a playlist.

        Args:
            playlist_id: ID of the playlist
            song_id: ID of the song to remove

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM playlist_songs WHERE playlist_id = ? AND song_id = ?",
                (playlist_id, song_id)
            )

            # Update playlist updated_at timestamp
            cursor.execute(
                "UPDATE playlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (playlist_id,)
            )

            self.conn.commit()

            if cursor.rowcount > 0:
                self.logger.info(f"Removed song {song_id} from playlist {playlist_id}")
                return True
            else:
                self.logger.warning(f"Song {song_id} not found in playlist {playlist_id}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove song from playlist: {e}")
            self.conn.rollback()
            return False