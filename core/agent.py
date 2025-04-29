import random
import re
import uuid
from typing import Dict

from api.broadcaster_client import BroadcasterAPIClient
from api.conversation_memory_api import APIBackedConversationMemory
from tools.broadcaster_tools import SoundFragmentTool, QueueTool
from tools.interaction_tools import InteractionTool

class AIDJAgent:
    def __init__(self, config: Dict, brand: str, api_client: BroadcasterAPIClient):
        self.song_fetch_tool = SoundFragmentTool(config)
        self.api_client = api_client
        self.memory = APIBackedConversationMemory(
            brand=brand,
            api_client=self.api_client
        )
        self.intro_tool = InteractionTool(config, self.memory)
        self.broadcast_tool = QueueTool(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self.brand = brand

    def run(self) -> None:
        print(f"Starting DJ Agent run for brand: {self.brand}")
        self._attempt_broadcast()
        print(f"DJ Agent run completed for brand: {self.brand}")

    def _attempt_broadcast(self) -> None:
        songs = self.song_fetch_tool.fetch_songs(self.brand)
        if not songs:
            print("No songs available")
            return

        song = random.choice(songs)
        song_uuid = song.get("id", str(uuid.uuid4()))
        details = song.get("soundFragmentDTO", {})
        title = re.sub(r'^[^a-zA-Z]*', '', details.get("title", ""))
        artist = details.get("artist", "")

        audio_data = self.intro_tool.create_introduction(title, artist, self.brand)

        if audio_data:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, audio_data):
                print(f"Broadcasted: {title} by {artist}")
        else:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, None):
                print(f"Playing directly: {title}")