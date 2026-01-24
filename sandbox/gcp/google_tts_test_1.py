import os
import time
from google.cloud import texttospeech_v1beta1 as texttospeech
from core.config import load_config

config = load_config("../../config.yaml")
google_tts_config = config.get("google_tts", {})
credentials_path = google_tts_config.get("credentials_path")

if not credentials_path or not os.path.exists(credentials_path):
    raise FileNotFoundError(f"Credentials file missing: {credentials_path}")

# 1. Initialize the client (v1beta1 is required for model_name)
client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)

# 2. Use Prosody Prompts for better DJ performance
# The [bracketed] text tells the Gemini model HOW to speak.
dj_phrases = [
    "[energetic, radio dj style] You're listening to the hottest beats online!",
    "[cool, smooth] Keep it locked right here."
]

metadata_dir = "../metadata"
os.makedirs(metadata_dir, exist_ok=True)

#voice_name = "en-US-Journey-D"
#voice_name = "en-US-Chirp3-HD-Puck"
#voice_name = "en-US-Chirp3-HD-Orus"
voice_name = "en-US-Chirp3-HD-Fenrir"
advanced_model = " gemini-1.5-pro"

print(f"Using Advanced Voice: {voice_name} via {advanced_model}")

for i, phrase in enumerate(dj_phrases):
    file_name = f"{metadata_dir}/dj_phrase_{i + 1}.mp3"
    if os.path.exists(file_name): continue

    print(f"Converting: '{phrase}'")

    try:
        # THE FIX: Put the model inside VoiceSelectionParams as 'model_name'
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            #model_name=advanced_model  # This is the correct field name
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        synthesis_input = texttospeech.SynthesisInput(text=phrase)

        # Execute call without a top-level 'model' field
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(file_name, "wb") as f:
            f.write(response.audio_content)

        print(f"Saved: {file_name}")
        time.sleep(0.5)

    except Exception as e:
        print(f"Error: {e}")

print("\nProcess complete!")