# tools/broadcaster_tools.py
import requests


class SoundFragmentTool:

    def __init__(self, config):
        self.api_base_url = config.get("BROADCASTER_API_BASE_URL", "http://localhost:38707/api")
        self.api_key = config.get("BROADCASTER_API_KEY", "")
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 10)

    def fetch_songs(self):
        try:
            response = requests.get(
                f"{self.api_base_url}/thomas-lee/soundfragments/available-soundfragments",
                headers=self._get_headers(),
                timeout=self.api_timeout
            )
            response.raise_for_status()
            data = response.json()
            songs = data["payload"]["viewData"]["entries"]
            print(f"Fetched {len(songs)} available songs")
            return songs
        except requests.RequestException as e:
            print(f"Error fetching available songs: {e}")
            return []

    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class QueueTool:

    def __init__(self, config):
        self.api_base_url = config.get("BROADCASTER_API_BASE_URL", "http://localhost:38707/api")
        self.api_key = config.get("BROADCASTER_API_KEY", "")
        self.api_timeout = config.get("BROADCASTER_API_TIMEOUT", 10)

    def send_to_broadcast(self, song_uuid, audio_data):
        try:
            response = requests.post(
                f"{self.api_base_url}/thomas-lee/queue/{song_uuid}",
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