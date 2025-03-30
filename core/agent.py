import random
import re
import time
import uuid
from typing import Dict

from tools.broadcaster_tools import SoundFragmentTool, QueueTool
from tools.content_tools import IntroductionTool


class AIDJAgent:
    def __init__(self, config: Dict, brand: str):
        self.song_fetch_tool = SoundFragmentTool(config)
        self.intro_tool = IntroductionTool(config)
        self.broadcast_tool = QueueTool(config)
        self.min_broadcast_interval: int = 200  # seconds
        self.last_broadcast: float = 0.0
        self.brand = brand

    def run(self) -> None:
        print(f"Starting DJ Agent run for brand: {self.brand}")

        # Do just one broadcast attempt
        self._attempt_broadcast()

        print(f"DJ Agent run completed for brand: {self.brand}")

        # No while loop, function completes

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

        audio_data = self.intro_tool.create_introduction(song, artist, self.brand)

        if audio_data:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, audio_data):
                print(f"Broadcasted: {title} by {artist}")
        else:
            if self.broadcast_tool.send_to_broadcast(self.brand, song_uuid, None):
                print(f"Playing directly: {title}")