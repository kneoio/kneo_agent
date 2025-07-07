import os
import random
import time

from dotenv import load_dotenv
from google.cloud import texttospeech

load_dotenv()

credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if credentials_path and os.path.exists(credentials_path):
    client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)
else:
    client = texttospeech.TextToSpeechClient()

dj_phrases = [
    "You're listening to the hottest beats online",
    "Keep it locked right here",
    "We're commercial-free for the next hour",
    "Don't touch that dial",
    "Text your requests now",
    "Up next, another great track",
    "You're in the mix",
    "That throwback jam taking you back",
    "We're keeping it hot with these tracks",
    "Shout out to everyone tuning in",
    "Taking you into the weekend with this next set",
    "Don't forget to follow us online",
    "This one's climbing the charts",
    "Perfect vibes for your day",
    "You heard it here first",
    "Back-to-back hits coming your way",
    "Let's slow things down",
    "Thanks for joining the conversation",
    "Stay tuned for more great music",
    "Keeping the rhythm going all day long"
]

metadata_dir = "metadata"
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir)

voices = client.list_voices()
print("Available English voices:")
for voice in voices.voices:
    if voice.language_codes[0].startswith('en'):
        print(f"- {voice.name} ({voice.ssml_gender.name})")

voice_name = "en-US-Wavenet-D"
print(f"Using voice: {voice_name}")

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name=voice_name,
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
)

for i, phrase in enumerate(dj_phrases):
    file_name = f"{metadata_dir}/dj_phrase_{i + 1}.mp3"

    if os.path.exists(file_name):
        print(f"File {file_name} already exists, skipping...")
        continue

    print(f"Converting phrase {i + 1}/{len(dj_phrases)}: '{phrase}'")

    try:
        synthesis_input = texttospeech.SynthesisInput(text=phrase)

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