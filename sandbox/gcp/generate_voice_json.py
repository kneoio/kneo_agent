import os
import json
from google.cloud import texttospeech_v1beta1 as texttospeech
from core.config import load_config

# Setup Client
config = load_config("../../config.yaml")
credentials_path = config.get("google_tts", {}).get("credentials_path")
client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)


def generate_labeled_json():
    print("Fetching global voices and applying quality labels...")
    response = client.list_voices()

    voice_list = []

    gender_map = {
        texttospeech.SsmlVoiceGender.MALE: "Male",
        texttospeech.SsmlVoiceGender.FEMALE: "Female",
        texttospeech.SsmlVoiceGender.NEUTRAL: "Neutral"
    }

    # Helper function to categorize voices
    def get_voice_metadata(voice_name):
        # TIER 1: The Best (Generative)
        if "Chirp" in voice_name or "Journey" in voice_name:
            return {
                "label": "Ultra-Realistic (Gemini)",
                "tag": "premium",
                "rank": 1,  # Used for sorting
                "short_name": voice_name.split('-')[-1]  # Just "Puck" or "Charon"
            }

        # TIER 2: Professional Recordings
        elif "Studio" in voice_name:
            return {
                "label": "Pro Studio",
                "tag": "premium",
                "rank": 2,
                "short_name": f"Studio-{voice_name.split('-')[-1]}"
            }

        # TIER 3: High Quality AI
        elif "Neural2" in voice_name:
            return {
                "label": "Enhanced AI",
                "tag": "balanced",
                "rank": 3,
                "short_name": f"Neural-{voice_name.split('-')[-1]}"
            }

        # TIER 4: Standard/Economy
        elif "Wavenet" in voice_name:
            return {
                "label": "Economy",
                "tag": "cheap",
                "rank": 4,
                "short_name": f"WaveNet-{voice_name.split('-')[-1]}"
            }

        # TIER 5: Legacy
        else:
            return {
                "label": "Legacy",
                "tag": "deprecated",
                "rank": 5,
                "short_name": voice_name  # Keep full name
            }

    # Process all voices
    for voice in response.voices:
        meta = get_voice_metadata(voice.name)

        # Exclude "Legacy" voices to keep your app clean
        if meta["rank"] == 5:
            continue

        voice_obj = {
            "id": voice.name,  # Full ID for API
            "name": meta["short_name"],  # Clean name for UI
            "gender": gender_map.get(voice.ssml_gender, "Unknown"),
            "language": voice.language_codes[0],
            "label": meta["label"],  # Descriptive text
            "tag": meta["tag"],  # Code-friendly tag (premium/cheap)
            "_rank": meta["rank"]  # Internal sorting helper
        }

        voice_list.append(voice_obj)

    # SORTING:
    # 1. By Language (A-Z)
    # 2. By Quality Rank (Best first)
    # 3. By Gender
    sorted_voices = sorted(
        voice_list,
        key=lambda k: (k['language'], k['_rank'], k['gender'])
    )

    # Remove the internal '_rank' key before saving (optional, keeps JSON clean)
    for v in sorted_voices:
        del v['_rank']

    output_file = "labeled_voices.json"
    with open(output_file, "w") as f:
        json.dump(sorted_voices, f, indent=2)

    print(f"Success! Saved {len(sorted_voices)} voices to {output_file}")


if __name__ == "__main__":
    generate_labeled_json()