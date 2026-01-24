import os
from google.cloud import texttospeech_v1beta1 as texttospeech
from core.config import load_config

config = load_config("../../config.yaml")
credentials_path = config.get("google_tts", {}).get("credentials_path")
client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)


def list_dj_voices():
    print("Fetching and filtering for 'DJ Quality' voices...\n")
    response = client.list_voices()

    # We only want US English for now
    target_lang = "en-US"

    print(f"{'FULL VOICE ID':<40} | {'GENDER':<8} | {'STYLE'}")
    print("-" * 70)

    voices = sorted(response.voices, key=lambda v: v.name)

    for voice in voices:
        if target_lang in voice.language_codes:
            name = voice.name
            gender = "Male" if voice.ssml_gender == texttospeech.SsmlVoiceGender.MALE else "Female"

            # FILTER: Only keep Chirp (Generative) and Studio (Pro)
            if "Chirp3-HD" in name:
                # These usually have names like 'Puck', 'Charon' at the end
                short_name = name.split('-')[-1]
                print(f"{name:<40} | {gender:<8} | Generative AI ({short_name})")

            elif "Studio" in name:
                print(f"{name:<40} | {gender:<8} | Professional Studio")


if __name__ == "__main__":
    list_dj_voices()
