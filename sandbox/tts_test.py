from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os
import time
import random

load_dotenv()

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

dj_phrases = [
 #   "You're listening to the hottest beats online",
 #   "Keep it locked right here",
 #   "We're commercial-free for the next hour",
 #   "Don't touch that dial",
 #   "Text your requests now",
 #   "Up next, another great track",
 #   "You're in the mix",
 #   "That throwback jam taking you back",
 #   "We're keeping it hot with these tracks",
 #   "Shout out to everyone tuning in",
 #   "Taking you into the weekend with this next set",
 #   "Don't forget to follow us online",
 #   "This one's climbing the charts",
 #   "Perfect vibes for your day",
 #   "You heard it here first",
 #   "Back-to-back hits coming your way",
 #   "Let's slow things down",
 #   "Thanks for joining the conversation",
 #   "Stay tuned for more great music",
 #   "Keeping the rhythm going all day long"
]


metadata_dir = "metadata"
if not os.path.exists(metadata_dir):
    os.makedirs(metadata_dir)


voice_response = client.voices.get_all()
print("Available voices:")
for voice in voice_response.voices:
    print(f"- {voice.name}: {voice.voice_id}")

selected_voice_id = "JBFqnCBsd6RMkjVDRZzb"
print(f"Selected voice ID: {selected_voice_id}")


for i, phrase in enumerate(dj_phrases):
    file_name = f"{metadata_dir}/dj_phrase_{i + 1}.mp3"

    if os.path.exists(file_name):
        print(f"File {file_name} already exists, skipping...")
        continue

    print(f"Converting phrase {i + 1}/{len(dj_phrases)}: '{phrase}'")

    try:
        audio = client.text_to_speech.convert(
            text=phrase,
            voice_id=selected_voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )

        with open(file_name, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        print(f"Audio saved to {file_name}")


        time.sleep(1)

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