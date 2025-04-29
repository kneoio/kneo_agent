# tools/broadcaster_tools.py
import requests
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast, Optional, Dict

T = TypeVar('T')


def cached(expiration_time: int = 300) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: Dict[str, Any] = {'data': None, 'timestamp': 0}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_time = int(time.time())
            if (current_time - cache['timestamp'] <= expiration_time and
                    cache['data'] is not None and
                    cache['data'] != []):
                print("Using cached data")
                return cast(T, cache['data'])

            result = func(*args, **kwargs)
            if isinstance(result, list) and result:
                cache['data'] = result
                cache['timestamp'] = current_time
                print("Cache updated with fresh data")
            return result

        return wrapper

    return decorator


class BaseBroadcasterTool:
    def __init__(self, config: Dict[str, Any]):
        self.api_base_url = config.get("BROADCASTER_API_BASE_URL")
        self.api_key = config.get("BROADCASTER_API_KEY", "")
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 10)

    def _get_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        try:
            response = requests.request(
                method,
                endpoint,
                headers=self._get_headers(kwargs.pop('content_type', None)),
                timeout=self.api_timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            return None


class SoundFragmentTool(BaseBroadcasterTool):
    @cached(expiration_time=300)  # 5 minutes cache
    def fetch_songs(self, brand: str) -> list:
        endpoint = f"{self.api_base_url}/{brand}/soundfragments/available-soundfragments"
        response = self._make_request('GET', endpoint, content_type="application/json")

        if not response:
            return []

        data = response.json()
        songs = data["payload"]["viewData"]["entries"]
        print(f"Fetched {len(songs)} available songs")
        return songs if songs else []  # Ensure we return empty list rather than None


class QueueTool(BaseBroadcasterTool):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Override default timeout for QueueTool
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 100)

    def send_to_broadcast(self, brand: str, song_uuid: str, audio_data: bytes) -> bool:
        endpoint = f"{self.api_base_url}/{brand}/queue/{song_uuid}"
        try:
            response = requests.post(
                endpoint,
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