import time
from tools.broadcaster_tools import SoundFragmentTool, QueueTool
from tools.content_tools import IntroductionTool
import random
import uuid

class AIDJWaker:
    def __init__(self, config):
        self.agent = AIDJAgent(config)
        self.wake_interval = 240  # 4 minutes in seconds

    def run(self):
        print("Starting DJ Waker - will wake agent every 4 minutes")
        while True:
            try:
                print("\n--- Waking up AI Agent ---")
                self.agent.run_once()  # We'll modify AIDJAgent to have this method
                print(f"\n--- Waker sleeping for {self.wake_interval//60} minutes ---")
                time.sleep(self.wake_interval)
            except Exception as e:
                print(f"Error in waker: {e}")
                time.sleep(60)  # Sleep shorter time on error

# Modified AIDJAgent with run_once method
class AIDJAgent:
    def __init__(self, config):
        self.song_fetch_tool = SoundFragmentTool(config)
        self.intro_tool = IntroductionTool(config)
        self.broadcast_tool = QueueTool(config)

    def run_once(self):
        """Run one complete cycle of song selection and broadcasting"""
        try:
            songs = self.song_fetch_tool.fetch_songs()
            if not songs:
                print("No songs available - skipping this cycle")
                return False

            selected_song = random.choice(songs)
            song_uuid = selected_song.get("id", str(uuid.uuid4()))
            sound_fragment = selected_song.get("soundFragmentDTO", {})

            song_title = sound_fragment.get("title", "Unknown")
            song_artist = sound_fragment.get("artist", "Unknown")

            audio_data = self.intro_tool.create_introduction(selected_song, song_artist)

            if audio_data:
                success = self.broadcast_tool.send_to_broadcast(song_uuid, audio_data)
                if success:
                    print(f"Successfully sent introduction for: {song_title}")
                    return True
            else:
                success = self.broadcast_tool.send_to_broadcast(song_uuid, None)
                if success:
                    print(f"Playing song without introduction: {song_title}")
                    return True

            return False
        except Exception as e:
            print(f"Error in agent run_once: {e}")
            return False

# Example usage
if __name__ == "__main__":
    config = {
        "BROADCASTER_API_BASE_URL": "http://localhost:38707/api",
        "BROADCASTER_API_KEY": "",
        "BROADCASTER_API_TIMEOUT": 10
    }
    waker = AIDJWaker(config)
    waker.run()