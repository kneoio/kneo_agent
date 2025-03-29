# core/agent.py
import random
import time
import uuid

# Tool imports
from tools.broadcaster_tools import SongFetchTool, BroadcastTool
from tools.content_tools import IntroductionTool, TTSTool


class AIDJAgent:
    def __init__(self, config):
        # Initialize tools
        self.song_fetch_tool = SongFetchTool(config)
        self.intro_tool = IntroductionTool(config)
        self.tts_tool = TTSTool(config)
        self.broadcast_tool = BroadcastTool(config)

    def run(self):
        print("Starting DJ Agent run loop")

        while True:
            try:
                # Use song fetch tool
                songs = self.song_fetch_tool.fetch_songs()
                if not songs:
                    time.sleep(30)
                    continue

                # Select random song
                selected_song = random.choice(songs) if songs else None
                if not selected_song:
                    time.sleep(30)
                    continue

                song_uuid = selected_song.get("uuid", str(uuid.uuid4()))

                # Use intro generation tool
                introduction = self.intro_tool.create_introduction(selected_song)

                # Use TTS tool
                audio_data = self.tts_tool.convert_to_speech(introduction)
                if not audio_data:
                    time.sleep(10)
                    continue

                # Use broadcast tool
                success = self.broadcast_tool.send_broadcast(song_uuid, audio_data)
                if success:
                    print(f"Successfully broadcasted song: {selected_song.get('title')}")

                time.sleep(60)

            except Exception as e:
                print(f"Error in DJ Agent run loop: {e}")
                time.sleep(30)