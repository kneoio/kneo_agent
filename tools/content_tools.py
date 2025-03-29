import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
import json
import re

load_dotenv()


class IntroductionTool:
    def __init__(self, config):
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist"],
            template="""
            You are a radio DJ. Introduce "{song_title}" by {artist}.
            Keep it short (10-30 words) and mention "AI Radio".
            """
        )

        self.filename_parse_prompt = PromptTemplate(
            input_variables=["filename"],
            template="""
            Parse this music filename into artist and title. Return only a JSON object with "artist" and "title" keys.
            If you can't reliably determine both, return null values.

            Filename: {filename}
            """
        )

    def parse_filename_with_llm(self, filename):
        try:
            print(f"Trying to recognize filename: {filename}")
            prompt = self.filename_parse_prompt.format(filename=filename)
            response = self.llm.invoke(prompt)
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group(0))
                return parsed_data
            return {"artist": None, "title": None}

        except Exception as e:
            print(f"Filename parsing error: {e}")
            return {"artist": None, "title": None}

    def create_introduction(self, song):
        try:
            title = song.get("title", None)
            artist = song.get("artist", None)
            if (not title or not artist) and "filename" in song:
                filename = song["filename"]
                parsed_data = self.parse_filename_with_llm(filename)

                if parsed_data.get("title"):
                    title = parsed_data.get("title")
                if parsed_data.get("artist"):
                    artist = parsed_data.get("artist")

            if not title or not artist or title == "Unknown Title" or artist == "Unknown Artist":
                return None

            prompt = self.intro_prompt_template.format(song_title=title, artist=artist)
            response = self.llm.invoke(prompt)
            return response.content

        except Exception as e:
            print(f"Introduction error: {e}")
            return None


class TTSTool:

    def __init__(self, config):
        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )

    def convert_to_speech(self, text):
        if not text:
            return None

        try:
            audio = self.client.text_to_speech.convert(
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            return b''.join(audio)
        except Exception as e:
            print(f"TTS error: {e}")
            return None