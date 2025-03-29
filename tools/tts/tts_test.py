from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os

load_dotenv()

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

# Get all available voices
voice_response = client.voices.get_all()
print("Available voices:")
for voice in voice_response.voices:
    print(f"- {voice.name}: {voice.voice_id}")

selected_voice_id = voice_response.voices[0].voice_id if voice_response.voices else "JBFqnCBsd6RMkjVDRZzb"

text_to_convert = "Ladies and gentlemen, please welcome to the stage... The Eagles with \"Hotel California!\""
audio = client.text_to_speech.convert(
    text=text_to_convert,
    voice_id=selected_voice_id,
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

with open("output_speech.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)
print(f"Audio saved to output_speech.mp3 using voice ID: {selected_voice_id}")