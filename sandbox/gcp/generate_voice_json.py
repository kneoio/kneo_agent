import os
import json
from google.cloud import texttospeech_v1beta1 as texttospeech
from core.config import load_config

config = load_config("../../config.yaml")
credentials_path = config.get("google_tts", {}).get("credentials_path")
client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)


def generate_lowercase_json():
    print("Generating voice list (lowercase labels)...")
    response = client.list_voices()

    voice_list = []

    # Map to lowercase strings
    gender_map = {
        texttospeech.SsmlVoiceGender.MALE: "male",
        texttospeech.SsmlVoiceGender.FEMALE: "female",
        texttospeech.SsmlVoiceGender.NEUTRAL: "neutral"
    }

    def get_tier_and_name(voice_name):
        parts = voice_name.split('-')

        # 1. PREMIUM (Chirp / Studio)
        if any(x in voice_name for x in ["Chirp", "Journey", "Studio"]):
            if "Chirp" in voice_name or "Journey" in voice_name:
                display_name = parts[-1]
            else:
                display_name = f"Studio-{parts[-1]}"
            return "premium", display_name

        # 2. STANDARD (Neural2 / Polyglot)
        elif "Neural2" in voice_name or "Polyglot" in voice_name:
            return "standard", f"Neural-{parts[-1]}"

        # 3. ECONOMY (WaveNet)
        elif "Wavenet" in voice_name:
            return "economy", f"WaveNet-{parts[-1]}"

        else:
            return "legacy", voice_name

    for voice in response.voices:
        tier, display_name = get_tier_and_name(voice.name)

        if tier == "legacy": continue

        voice_obj = {
            "id": voice.name,
            "name": display_name,
            "gender": gender_map.get(voice.ssml_gender, "unknown"),  # lowercase
            "language": voice.language_codes[0],
            "labels": tier  # lowercase: "premium", "standard", "economy"
        }

        voice_list.append(voice_obj)

    sorted_voices = sorted(voice_list, key=lambda k: (k['language'], k['name']))

    output_file = "dj_voices_final.json"
    with open(output_file, "w") as f:
        json.dump(sorted_voices, f, indent=2)

    print(f"Success! Saved lowercase list to {output_file}")


if __name__ == "__main__":
    generate_lowercase_json()
