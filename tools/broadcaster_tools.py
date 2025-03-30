# tools/broadcaster_tools.py
import requests
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

T = TypeVar('T')


def cached(expiration_time: int = 300) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: dict[str, Any] = {'data': None, 'timestamp': 0}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_time = int(time.time())  # Ensure timestamp is int
            # Only use cache if not expired AND data exists AND not empty/error
            if (current_time - cache['timestamp'] <= expiration_time and
                    cache['data'] is not None and
                    cache['data'] != []):  # Assuming empty list means no songs
                print("Using cached data")
                return cast(T, cache['data'])

            # Fetch fresh data
            result = func(*args, **kwargs)
            # Only cache if result is valid (not empty and no error)
            if isinstance(result, list) and result:  # Assuming we expect a non-empty list
                cache['data'] = result
                cache['timestamp'] = current_time
                print("Cache updated with fresh data")
            return result

        return wrapper

    return decorator


class SoundFragmentTool:

    def __init__(self, config):
        self.api_base_url = config.get("BROADCASTER_API_BASE_URL", "http://localhost:38707/api")
        self.api_key = config.get("BROADCASTER_API_KEY", "")
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 10)

    @cached(expiration_time=300)  # 5 minutes cache
    def fetch_songs(self, brand: str) -> list:
        try:
            response = requests.get(
                f"{self.api_base_url}/{brand}/soundfragments/available-soundfragments",
                headers=self._get_headers(),
                timeout=self.api_timeout
            )
            response.raise_for_status()
            data = response.json()
            songs = data["payload"]["viewData"]["entries"]
            print(f"Fetched {len(songs)} available songs")
            return songs if songs else []  # Ensure we return empty list rather than None
        except requests.RequestException as e:
            print(f"Error fetching available songs: {e}")
            return []  # Return empty list on error

    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class QueueTool:

    def __init__(self, config):
        self.api_base_url = config.get("BROADCASTER_API_BASE_URL", "http://localhost:38707/api")
        self.api_key = config.get("BROADCASTER_API_KEY", "")
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 100)

    def send_to_broadcast(self, brand: str, song_uuid: str, audio_data: bytes) -> bool:
        try:
            response = requests.post(
                f"{self.api_base_url}/{brand}/queue/{song_uuid}",
                headers=self._get_headers(),
                timeout=self.api_timeout,
                data={"song_uuid": song_uuid},
                files={"intro_audio": ("intro.mp3", audio_data, "audio/mpeg")}
            )
            response.raise_for_status()
            print(f"Successfully submitted broadcast for song {song_uuid}")
            return True
        except requests.RequestException as e:
            print(f"Error submitting to broadcaster: {e}")
            return False

    def _get_headers(self):
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers