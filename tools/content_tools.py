# tools/content_tools.py
import requests
from langchain.prompts import PromptTemplate
from langchain.llms.anthropic import ChatAnthropic


class IntroductionTool:
    """Tool to generate song introductions using Claude."""

    def __init__(self, config):
        # Initialize Claude model
        self.llm = ChatAnthropic(
            model="claude-3-7-sonnet-20250219",
            temperature=0.7,
            api_key=config.get("ANTHROPIC_API_KEY", "")
        )

        # Set up prompt template
        self.prompt_template = PromptTemplate(
            input_variables=["song_title", "artist"],
            template="""
            You are an enthusiastic radio DJ. Create a brief, engaging introduction for the song "{song_title}" by {artist}.
            Your introduction should be conversational, authentic, and between 3-8 seconds when spoken (about 10-30 words).
            Occasionally mention the radio station name "AI Radio" and add some personality.
            """
        )

    def create_introduction(self, song):
        """Generate a DJ introduction for the selected song."""
        try:
            # Extract title and artist
            title = song.get("title", "Unknown Title")
            artist = song.get("artist", "Unknown Artist")

            # Extract from filename if needed
            if title == "Unknown Title" and "filename" in song:
                filename = song["filename"]
                parts = filename.split('-')
                if len(parts) >= 2:
                    artist = parts[0].strip()
                    title = parts[1].strip().split('.')[0]

            # Generate introduction
            prompt = self.prompt_template.format(song_title=title, artist=artist)
            response = self.llm.invoke(prompt)
            introduction = response.content[0].text.strip()

            print(f"Created introduction: {introduction}")
            return introduction

        except Exception as e:
            print(f"Error creating song introduction: {e}")
            return f"Now playing: {song.get('title', 'our next track')} by {song.get('artist', 'an amazing artist')}"


class TTSTool:
    """Tool to convert text to speech using ElevenLabs."""

    def __init__(self, config):
        self.api_key = config.get("ELEVENLABS_API_KEY", "")

    def convert_to_speech(self, text):
        """Convert text to speech using ElevenLabs API."""
        try:
            response = requests.post(
                "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",  # Default voice ID
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.api_key
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )
            response.raise_for_status()
            print("Successfully generated TTS audio")
            return response.content
        except requests.RequestException as e:
            print(f"Error in text-to-speech conversion: {e}")
            return None