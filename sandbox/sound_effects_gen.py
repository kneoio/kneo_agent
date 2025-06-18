# sandbox/sound_effects_gen.py

import os

from elevenlabs import ElevenLabs

from core.config import load_config

config_file_path = "../config.yaml"
config = load_config(config_file_path)
metadata_dir = "metadata"
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir)

file_name = f"{metadata_dir}/effect.mp3"

client = ElevenLabs(
    api_key=config.get("elevenlabs", {}).get("api_key"),
)
effect = client.text_to_sound_effects.convert(
    text="Spacious braam suitable for high-impact movie trailer moments",
)

with open(file_name, "wb") as f:
    for chunk in effect:
        f.write(chunk)

print(f"Audio saved to {file_name}")