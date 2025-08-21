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

audio_stream = client.text_to_speech.convert(
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    output_format="mp3_44100_128",
    text="Testing ElevenLabs text-to-speech conversion.",
    #model_id="eleven_multilingual_v2",
    model_id="eleven_v3",
)

with open("test_basic.mp3", "wb") as f:
    for chunk in audio_stream:
        if chunk:
            f.write(chunk)

print("Generated test_basic.mp3")