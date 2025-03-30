#!/usr/bin/env python3
import logging
import os
from api.song_queue_api import SongQueueAPI
from api.broadcaster_client import BroadcasterAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test parameters
BRAND_ID = 'hartman-torres'
LIMIT = 10
SONG_ID = 'song1'  # Will need a valid ID from get_available_songs


def test_api_connection():
    # Check environment variables
    api_key = os.getenv("BROADCASTER_API_KEY")
    base_url = os.getenv("BROADCASTER_API_BASE_URL")

    if not api_key or not base_url:
        logger.error("Missing environment variables: BROADCASTER_API_KEY or BROADCASTER_API_BASE_URL")
        return False

    # Test direct API connection
    client = BroadcasterAPIClient(base_url=base_url, api_key=api_key)
    try:
        # Test a simple GET request
        response = client.get("available-soundfragments", {"limit": 1, "brand": BRAND_ID})
        logger.info(f"Direct API response: {response}")
        return response is not None
    except Exception as e:
        logger.error(f"API connection test failed: {e}")
        return False


def main():
    if not test_api_connection():
        logger.error("API connection test failed. Check your credentials and server.")
        return

    # Initialize the API client
    api = SongQueueAPI()

    # Test get_available_songs
    logger.info("Testing get_available_songs")
    songs = api.get_available_songs(limit=LIMIT, brand_id=BRAND_ID)

    if not songs:
        logger.error("No songs found. API might not be working correctly.")
        return

    logger.info(f"Found {len(songs)} songs")
    for i, song in enumerate(songs[:5]):
        logger.info(f"{i + 1}. {song.title} by {song.artist}")

        # Use the first song's ID for other tests
        if i == 0:
            SONG_ID = song.id

    # Test add_song with a valid ID
    logger.info(f"Testing add_song with ID: {SONG_ID}")
    success = api.add_song(song_id=SONG_ID, brand_id=BRAND_ID)
    logger.info(f"Added song to queue: {'Success' if success else 'Failed'}")

    # Test get_queue
    logger.info("Testing get_queue")
    queue = api.get_queue(brand_id=BRAND_ID)
    logger.info(f"Queue has {len(queue)} songs")
    for i, song in enumerate(queue):
        logger.info(f"{i + 1}. {song.title} by {song.artist}")

    # Test get_current_song
    logger.info("Testing get_current_song")
    song = api.get_current_song(brand_id=BRAND_ID)
    if song:
        logger.info(f"Current song: {song.title} by {song.artist}")
    else:
        logger.info("No song is currently playing")


if __name__ == "__main__":
    main()