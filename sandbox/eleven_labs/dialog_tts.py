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
    inputs=[
        {
            "text": "You ever notice how some tracks feel like a ritual? Not just music — something ancient in a machine rhythm.",
            "voice_id": "9BWtsMINqrJLrRacOk9x"
        },
        {
            "text": "Exactly. The pulse, the reverb — it’s like a congregation under strobe lights. Tonight we revisit one of those hymns.",
            "voice_id": "IKne3meq5aSn9XLyUdCD"
        },
        {
            "text": "This is 'House of God' — 1991 Original Italian Remix by D.H.S. Let it take you where words stop working.",
            "voice_id": "9BWtsMINqrJLrRacOk9x"
        }
    ]
)

with open("test_basic.mp3", "wb") as f:
    for chunk in audio_stream:
        if chunk:
            f.write(chunk)

print("Generated test_basic.mp3")
