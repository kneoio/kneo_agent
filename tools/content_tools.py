import logging
import os
import random
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

load_dotenv()


class IntroductionTool:
    def __init__(self, config):
        # Existing LLM and TTS setup
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )

        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist"],
            template="""
            You are a radio DJ. Introduce "{song_title}" by {artist}.
            Keep it short (10-30 words) and mention radio station name: "thomas-lee".              
            """
        )

        self.metadata_folder = config.get("METADATA_FOLDER", "metadata/prologue/JBFqnCBsd6RMkjVDRZzb")
        self.audio_files = self._load_audio_files()
        self.use_file_probability = config.get("USE_FILE_PROBABILITY", 0.4)  #0.3 30% chance to use a file

    def _load_audio_files(self):
        """Load all available audio files from the metadata folder"""
        audio_files = []
        metadata_path = Path(self.metadata_folder)

        if metadata_path.exists() and metadata_path.is_dir():
            for file in metadata_path.glob("*.mp3"):
                audio_files.append(file)

        print(f"Loaded {len(audio_files)} intro audio files from {self.metadata_folder}")
        return audio_files

    def _get_random_audio_file(self):
        """Get a random pre-recorded introduction audio file"""
        if not self.audio_files:
            return None

        selected_file = random.choice(self.audio_files)

        try:
            with open(selected_file, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading audio file {selected_file}: {e}")
            return None

    def create_introduction(self, title, artist):
        logger = logging.getLogger(__name__)

        try:
            logger.debug(f"Starting introduction for: {title} by {artist}")

            # 1. Try pre-recorded files first
            if self.audio_files:
                if random.random() < self.use_file_probability:
                    logger.debug(f"Attempting pre-recorded file (probability: {self.use_file_probability})")
                    audio = self._get_random_audio_file()
                    if audio:
                        logger.info("Using pre-recorded audio introduction")
                        return audio
                    logger.warning("Pre-recorded audio file found but failed to load")

            # 2. Skip invalid songs
            if not title or title == "Unknown":
                logger.debug("Skipping introduction - invalid song title")
                return None

            # 3. Generate text
            logger.debug("Generating LLM introduction")
            prompt = self.intro_prompt_template.format(
                song_title=title,
                artist=artist
            )
            response = self.llm.invoke(prompt)

            # 4. Extract clean content
            if not response:
                logger.error("Empty response from LLM")
                return None

            if not hasattr(response, 'content'):
                logger.error(f"Malformed LLM response: {type(response)}")
                return None

            tts_text = response.content.split("{")[0].strip()
            logger.debug(f"Generated introduction text: {tts_text[:100]}...")

            # 5. Generate TTS
            logger.debug("Calling ElevenLabs TTS API")
            audio = self.client.text_to_speech.convert(
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            logger.info("Successfully generated TTS introduction")
            return b''.join(audio)

        except Exception as e:
            logger.exception(f"Failed to create introduction: {str(e)}")
            return None
