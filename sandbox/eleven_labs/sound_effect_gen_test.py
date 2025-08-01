import argparse
from elevenlabs import ElevenLabs
from core.config import load_config

parser = argparse.ArgumentParser(description="Generate multiple jingles")
parser.add_argument("--config", default="../config.yaml", help="Path to configuration file")
args = parser.parse_args()

config = load_config(args.config)

client = ElevenLabs(
    api_key=config.get("elevenlabs").get("api_key")
)

# Define the genre variable
genre = "Industrial"

# Different jingle variations with same genre
jingle_variations = [
    {"text": f"{genre} Huge epic braam", "filename": "jingle_v1.mp3"},
    {"text": f"{genre} Eerie mood music", "filename": "jingle_v2.mp3"},
    {"text": f"Short {genre.lower()} ident with synth stabs and echo", "filename": "jingle_v3.mp3"},
    {"text": f"Dark {genre.lower()} transition jingle with industrial noise sweep", "filename": "jingle_v4.mp3"},
    {"text": f"Minimal {genre.lower()} bumper with rhythmic machinery sounds", "filename": "jingle_v5.mp3"}
]

for jingle in jingle_variations:
    audio_stream = client.text_to_sound_effects.convert(
        text = jingle["text"]
    )

    # Save the audio
    with open(jingle["filename"], "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)

    print(f"Generated {jingle['filename']} - {jingle['text']}")