import random
import re
import time
import uuid
from datetime import datetime, timedelta

# Tool imports
from tools.broadcaster_tools import SoundFragmentTool, QueueTool
from tools.content_tools import IntroductionTool


class AIDJAgent:
    def __init__(self, config):
        self.song_fetch_tool = SoundFragmentTool(config)
        self.intro_tool = IntroductionTool(config)
        self.broadcast_tool = QueueTool(config)
        self.sleep_time = 60

    def run(self):
        print("Starting DJ Agent run loop")
        MIN_TIME_BETWEEN_BROADCASTS = 200.0  # seconds between broadcasts
        TICK_INTERVAL = 10.0  # seconds between checks

        last_broadcast_time = 0.0

        while True:
            try:
                current_time = time.time()
                time_since_last = current_time - last_broadcast_time

                # Calculate time until next possible broadcast
                time_until_next = max(0.0, MIN_TIME_BETWEEN_BROADCASTS - time_since_last)
                mins, secs = divmod(int(time_until_next), 60)
                time_str = f"{mins:02d}:{secs:02d}"

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tick - {time_str} until wake up")

                # Only broadcast if minimum time has passed
                if time_since_last >= MIN_TIME_BETWEEN_BROADCASTS:
                    songs = self.song_fetch_tool.fetch_songs()
                    if songs:
                        selected_song = random.choice(songs)
                        song_uuid = selected_song.get("id", str(uuid.uuid4()))
                        sound_fragment = selected_song.get("soundFragmentDTO", {})
                        song_title = sound_fragment.get("title", "Unknown")
                        song_title = re.sub(r'^[^a-zA-Z]*', '', song_title)
                        song_artist = sound_fragment.get("artist", "Unknown")

                        audio_data = self.intro_tool.create_introduction(selected_song, song_artist)

                        if audio_data:
                            if self.broadcast_tool.send_to_broadcast(song_uuid, audio_data):
                                print(f"Broadcasted: {song_title} by {song_artist}")
                                last_broadcast_time = current_time
                        else:
                            if self.broadcast_tool.send_to_broadcast(song_uuid, None):
                                print(f"Playing directly: {song_title}")
                                last_broadcast_time = current_time
                    else:
                        print("No songs available")

                # Smart sleep calculation
                next_possible = last_broadcast_time + MIN_TIME_BETWEEN_BROADCASTS
                remaining_wait = max(0.0, next_possible - time.time())
                sleep_duration = min(TICK_INTERVAL, remaining_wait) if remaining_wait > 0 else TICK_INTERVAL

                time.sleep(sleep_duration)

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(TICK_INTERVAL)