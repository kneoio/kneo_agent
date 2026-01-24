import os
from google.cloud import texttospeech_v1beta1 as texttospeech
from core.config import load_config

# 1. Load Credentials just like your main app
config = load_config("../config.yaml")
google_tts_config = config.get("google_tts", {})
credentials_path = google_tts_config.get("credentials_path")

if not credentials_path or not os.path.exists(credentials_path):
    raise FileNotFoundError("Credentials file missing.")

client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)


def list_voices():
    # 2. Request the list of all voices
    print("Fetching available voices from Google Cloud...")
    response = client.list_voices()

    # 3. Filter and Sort
    # Let's filter for just US English (en-US) to keep the list readable
    target_lang = "en-US"

    print(f"\n--- VOICES FOR {target_lang} ---\n")
    print(f"{'VOICE NAME':<30} | {'GENDER':<10} | {'QUALITY / TYPE'}")
    print("-" * 65)

    # Helper to translate gender codes to text
    gender_map = {
        texttospeech.SsmlVoiceGender.MALE: "Male",
        texttospeech.SsmlVoiceGender.FEMALE: "Female",
        texttospeech.SsmlVoiceGender.NEUTRAL: "Neutral",
        texttospeech.SsmlVoiceGender.SSML_VOICE_GENDER_UNSPECIFIED: "Unknown"
    }

    voices = sorted(response.voices, key=lambda v: v.name)

    for voice in voices:
        # Check if this voice supports our target language
        if target_lang in voice.language_codes:

            name = voice.name
            gender = gender_map[voice.ssml_gender]

            # Determine Quality/Type based on the name
            if "Journey" in name:
                quality = "Generative (Best - Conversational)"
            elif "Studio" in name:
                quality = "Studio (Professional Narration)"
            elif "Neural2" in name:
                quality = "Neural2 (High Quality AI)"
            elif "Wavenet" in name:
                quality = "WaveNet (Standard)"
            elif "Polyglot" in name:
                quality = "Polyglot (Multi-language)"
            else:
                quality = "Standard (Legacy)"

            print(f"{name:<30} | {gender:<10} | {quality}")


if __name__ == "__main__":
    list_voices()
