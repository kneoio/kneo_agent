import random
import time
import uuid

# Tool imports
from tools.broadcaster_tools import SoundFragmentTool, QueueTool
from tools.content_tools import IntroductionTool, TTSTool


class AIDJAgent:
    def __init__(self, config):
        self.song_fetch_tool = SoundFragmentTool(config)
        self.intro_tool = IntroductionTool(config)
        self.tts_tool = TTSTool(config)
        self.broadcast_tool = QueueTool(config)
        self.sleep_time = 30

    def run(self):
        print("Starting DJ Agent run loop")

        while True:
            try:
                songs = self.song_fetch_tool.fetch_songs()
                if not songs:
                    time.sleep(self.sleep_time)
                    continue
                selected_song = random.choice(songs) if songs else None
                if not selected_song:
                    time.sleep(5)
                    continue

                song_uuid = selected_song.get("id", str(uuid.uuid4()))
                song_title = selected_song.get("title", "Unknown")

                introduction = self.intro_tool.create_introduction(selected_song)

                audio_data = None
                if introduction:
                    audio_data = self.tts_tool.convert_to_speech(introduction)

                if audio_data:
                    success = self.broadcast_tool.send_to_broadcast(song_uuid, audio_data)
                    if success:
                        print(f"Successfully sent introduction for: {song_title}")
                else:
                    success = self.broadcast_tool.send_to_broadcast(song_uuid, None)
                    if success:
                        print(f"Playing song without introduction: {song_title}")

                time.sleep(5)

            except Exception as e:
                print(f"Error in DJ Agent run loop: {e}")
                time.sleep(5)