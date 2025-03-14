#!/usr/bin/env python3
# mock/music_api_server.py - Mock Music API Server

import logging
import json
import argparse
from flask import Flask, request, jsonify
from music_api_server import MockMusicAPI

# Create Flask app
app = Flask(__name__)

# Initialize MockMusicAPI
music_api = MockMusicAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@app.route('/api/songs/search', methods=['GET'])
def search_songs():
    """Search for songs based on various criteria."""
    # Extract query parameters
    criteria = {}
    for key in request.args:
        if key != 'limit':
            criteria[key] = request.args[key]

    limit = int(request.args.get('limit', 10))

    # Call mock API
    songs = music_api.search_songs(criteria, limit)

    return jsonify({
        "success": True,
        "data": songs,
        "count": len(songs)
    })


@app.route('/api/songs/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """Get a song by its ID."""
    song = music_api.get_song_by_id(song_id)

    if song:
        return jsonify({
            "success": True,
            "data": song
        })
    else:
        return jsonify({
            "success": False,
            "error": "Song not found"
        }), 404


@app.route('/api/songs', methods=['POST'])
def add_song():
    """Add a new song."""
    song_info = request.json

    song_id = music_api.add_song(song_info)

    if song_id:
        return jsonify({
            "success": True,
            "data": {
                "id": song_id
            },
            "message": "Song added successfully"
        }), 201
    else:
        return jsonify({
            "success": False,
            "error": "Invalid song data"
        }), 400


@app.route('/api/songs/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    """Update an existing song."""
    song_info = request.json

    success = music_api.update_song(song_id, song_info)

    if success:
        return jsonify({
            "success": True,
            "message": "Song updated successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Song not found"
        }), 404


@app.route('/api/songs/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    """Delete a song."""
    success = music_api.delete_song(song_id)

    if success:
        return jsonify({
            "success": True,
            "message": "Song deleted successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Song not found"
        }), 404


@app.route('/api/genres', methods=['GET'])
def get_genres():
    """Get all genres."""
    genres = music_api.get_genres()

    return jsonify({
        "success": True,
        "data": genres,
        "count": len(genres)
    })


@app.route('/api/artists', methods=['GET'])
def get_artists():
    """Get all artists."""
    artists = music_api.get_artists()

    return jsonify({
        "success": True,
        "data": artists,
        "count": len(artists)
    })


@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    """Get all playlists."""
    playlists = music_api.get_playlists()

    return jsonify({
        "success": True,
        "data": playlists,
        "count": len(playlists)
    })


@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    """Create a new playlist."""
    data = request.json
    name = data.get('name')
    description = data.get('description')

    playlist_id = music_api.create_playlist(name, description)

    if playlist_id:
        return jsonify({
            "success": True,
            "data": {
                "id": playlist_id
            },
            "message": "Playlist created successfully"
        }), 201
    else:
        return jsonify({
            "success": False,
            "error": "Invalid playlist data"
        }), 400


@app.route('/api/playlists/<int:playlist_id>/songs', methods=['POST'])
def add_to_playlist(playlist_id):
    """Add a song to a playlist."""
    data = request.json
    song_id = data.get('song_id')
    position = data.get('position')

    if not song_id:
        return jsonify({
            "success": False,
            "error": "Missing song_id"
        }), 400

    success = music_api.add_to_playlist(playlist_id, song_id, position)

    if success:
        return jsonify({
            "success": True,
            "message": "Song added to playlist successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to add song to playlist"
        }), 404


@app.route('/api/playlists/<int:playlist_id>/songs/<int:song_id>', methods=['DELETE'])
def remove_from_playlist(playlist_id, song_id):
    """Remove a song from a playlist."""
    success = music_api.remove_from_playlist(playlist_id, song_id)

    if success:
        return jsonify({
            "success": True,
            "message": "Song removed from playlist successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to remove song from playlist"
        }), 404


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a mock Music API server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to run the server on')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')

    args = parser.parse_args()

    logger.info(f"Starting mock Music API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)