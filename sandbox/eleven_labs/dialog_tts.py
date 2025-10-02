import argparse
from elevenlabs import ElevenLabs
from core.config import load_config

parser = argparse.ArgumentParser(description="Test ElevenLabs TTS")
parser.add_argument("--config", default="../../config.yaml", help="Path to configuration file")
args = parser.parse_args()

config = load_config(args.config)

client = ElevenLabs(
    api_key=config.get("elevenlabs").get("api_key")
)

audio_stream = client.text_to_dialogue.convert(
    inputs=[ { "text": "Hello, how are you?", "voice_id": "9BWtsMINqrJLrRacOk9x", },
             { "text": "I'm doing well, thank you!", "voice_id": "IKne3meq5aSn9XLyUdCD", } ] )

with open("test_basic.mp3", "wb") as f:
    for chunk in audio_stream:
        if chunk:
            f.write(chunk)

print("Generated test_basic.mp3")





