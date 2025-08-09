import time
import requests
from typing import Dict, Any, List

def cached(expiration_time: int = 300):
    def decorator(func):
        cache = {'data': None, 'timestamp': 0}

        def wrapper(*args, **kwargs):
            current_time = int(time.time())
            if current_time - cache['timestamp'] <= expiration_time and cache['data']:
                return cache['data']
            result = func(*args, **kwargs)
            if result:
                cache['data'] = result
                cache['timestamp'] = current_time
            return result
        return wrapper
    return decorator

class SoundFragment:
    def __init__(self, config: Dict[str, Any]):
        broadcaster = config.get("broadcaster", {})
        self.api_base_url = broadcaster.get("api_base_url")
        self.api_key = broadcaster.get("api_key")
        self.api_timeout = broadcaster.get("api_timeout", 60)

    def _get_headers(self, content_type: str = None) -> Dict[str, str]:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _make_request(self, method: str, endpoint: str, **kwargs):
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
            print(f"Request failed: {e}")  # Print the exception
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text}")
            return None

    @cached(expiration_time=60) #1 min
    def fetch_songs(self, brand: str) -> List[Dict[str, Any]]:
        endpoint = f"{self.api_base_url}/soundfragments/available-soundfragments?brand={brand}&page=1&size=10"
        response = self._make_request('GET', endpoint, content_type="application/json")
        return response.json()["payload"]["viewData"]["entries"] if response else []