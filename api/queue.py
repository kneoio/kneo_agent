from typing import Dict, Any, Optional
import logging
import requests


class Queue:
    def __init__(self, config: Dict[str, Any]):
        self.api_base_url = config.get("broadcaster").get("api_base_url")
        self.api_key = config.get("broadcaster").get("api_key")
        self.api_timeout = config.get("broadcaster").get("api_timeout")
        self.logger = logging.getLogger(__name__)

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
        except requests.RequestException:
            return None

    def send_to_broadcast(self, brand: str, song_uuid: str, audio_data: bytes) -> bool:
        endpoint = f"{self.api_base_url}/{brand}/queue/{song_uuid}"
        upload_timeout = self.api_timeout * 10

        try:
            self.logger.info(f"Broadcasting {song_uuid} to {brand}")

            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                timeout=upload_timeout,
                data={"song_uuid": song_uuid},
                files={"intro_audio": ("intro.mp3", audio_data, "audio/mpeg")}
            )

            response.raise_for_status()
            self.logger.info(f"########Broadcast successful###########: {brand} -------> {song_uuid}")
            return True

        except requests.exceptions.Timeout:
            self.logger.error(f"Broadcast timeout ({upload_timeout}s): {song_uuid}")
            return False

        except requests.exceptions.ConnectionError:
            self.logger.error(f"Broadcast connection failed: {song_uuid}")
            return False

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Broadcast HTTP {e.response.status_code}: {song_uuid}")
            return False

        except Exception as e:
            self.logger.error(f"Broadcast failed: {song_uuid} - {type(e).__name__}")
            return False

    def get_queue_status(self, brand: str) -> Optional[Dict[str, Any]]:
        endpoint = f"{self.api_base_url}/{brand}/queue/status"
        response = self._make_request('GET', endpoint)
        return response.json() if response else None