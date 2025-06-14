import random
import re
import uuid
from typing import Dict, List

from api.broadcaster_client import BroadcasterAPIClient
from api.interaction_memory import InteractionMemory
from tools.interaction_tools import InteractionTool
from tools.queue_tool import QueueTool
from tools.sound_fragment_tool import SoundFragmentTool


class AIDJAgent:
    def __init__(self, config: Dict, brand_config: Dict, language: str, api_client: BroadcasterAPIClient):
        self.brand_config = brand_config
        self.brand = brand_config.get('radioStationName')
        self.agent_config = brand_config.get('agent', {})

        self.song_fetch_tool = SoundFragmentTool(config)
        self.api_client = api_client
        self.memory = InteractionMemory(
            brand=self.brand,
            api_client=self.api_client
        )
        self.intro_tool = InteractionTool(config, self.memory, language, self.agent_config)
        self.broadcast_tool = QueueTool(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self.language = language

        self._played_songs_history: List[str] = []
        self._cooldown_songs_count: int = self.agent_config.get('songCooldown', 4)

    def run(self) -> None:
        print(f"Starting DJ Agent run for brand: {self.brand}")
        print(f"Agent name: {self.agent_config.get('name', 'Unknown')}")
        print(f"Preferred voice: {self.agent_config.get('preferredVoice', 'Default')}")
        self._feed_broadcast()
        print(f"DJ Agent run completed for brand: {self.brand}")

    def _feed_broadcast(self) -> None:
        songs = self.song_fetch_tool.fetch_songs(self.brand)
        if not songs:
            print("No songs available")
            return
        print(f"available {len(songs)}")

        playable_songs = [
            song for song in songs
            if song.get("id") not in self._played_songs_history
        ]

        if not playable_songs:
            print("All available songs are currently in cooldown. Choosing randomly from all songs.")
            song = random.choice(songs)
        else:
            song = random.choice(playable_songs)

        song_uuid = song.get("id", str(uuid.uuid4()))
        details = song.get("soundFragmentDTO", {})
        title = re.sub(r'^[^a-zA-Z]*', '', details.get("title", ""))
        artist = details.get("artist", "")

        self._played_songs_history.append(song_uuid)
        if len(self._played_songs_history) > self._cooldown_songs_count:
            self._played_songs_history.pop(0)

        audio_data = self.intro_tool.create_introduction(
            title,
            artist,
            self.brand,
            agent_config=self.agent_config
        )

        if audio_data:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, audio_data):
                print(f"Broadcasted: {title} by {artist}")
        else:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, None):
                print(f"Playing directly: {title}")