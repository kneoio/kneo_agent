import os
import random
import time

from google.cloud import texttospeech_v1
from google.cloud.texttospeech_v1.types import VoiceSelectionParams, AudioConfig, SynthesisInput
from core.config import load_config

config = load_config("../config.yaml")
google_tts_config = config.get("google_tts", {})

credentials_path = google_tts_config.get("credentials_path")

if not credentials_path:
    raise ValueError("Missing google_tts.credentials_path in config.yaml")

if not os.path.exists(credentials_path):
    raise FileNotFoundError(f"Google TTS credentials file not found: {credentials_path}")

client = texttospeech_v1.TextToSpeechClient.from_service_account_json(credentials_path)

dj_phrases = [
    "You're listening to the hottest beats online",
    "Keep it locked right here"
]

metadata_dir = "metadata"
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir)

#voices = client.list_voices()
#print("Available English voices:")
#for voice in voices.voices:
    #if voice.language_codes[0].startswith('en'):
#    print(f"name: {voice.name}   gender:{voice.ssml_gender.name}")

voice_name = "Charon"
#voice_name = "en-US-Wavenet-D"
#voice_name = "en-US-Studio-O"
print(f"Using voice: {voice_name}")

voice = VoiceSelectionParams({
    "language_code": "en-US",
    "name": voice_name,
    "model_name": "gemini-2.5-flash-preview-tts"
    #"model_name": "gemini-2.5-flash-tts"
    #"model_name": "gemini-2.5-pro-tts"

})

audio_config = AudioConfig({
    "audio_encoding": 2,
})

for i, phrase in enumerate(dj_phrases):
    file_name = f"{metadata_dir}/dj_phrase_{i + 1}.mp3"

    if os.path.exists(file_name):
        print(f"File {file_name} already exists, skipping...")
        continue

    print(f"Converting phrase {i + 1}/{len(dj_phrases)}: '{phrase}'")

    try:
        synthesis_input = SynthesisInput({"text": phrase})

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(file_name, "wb") as f:
            f.write(response.audio_content)

        print(f"Audio saved to {file_name}")
        time.sleep(0.5)

    except Exception as e:
        print(f"Error converting phrase {i + 1}: {e}")

print("\nAll phrases converted successfully!")

def get_random_dj_phrase():
    phrase_files = [f for f in os.listdir(metadata_dir) if f.startswith("dj_phrase_") and f.endswith(".mp3")]
    if phrase_files:
        return os.path.join(metadata_dir, random.choice(phrase_files))
    return None

print("\nExample of using the cached audio files:")
print(f"Random DJ phrase file: {get_random_dj_phrase()}")