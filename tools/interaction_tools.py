import json
import logging
import random
from pathlib import Path

from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from api.interaction_memory import InteractionMemory


class InteractionTool:
    def __init__(self, config, memory: InteractionMemory, language="en"):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.client = ElevenLabs(
            api_key=config.get("elevenlabs").get("api_key")
        )

        self.memory = memory
        self.language = language
        self.locales_folder = Path("prompt/interaction")
        self.language_data = self._load_language_data()

        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist", "brand", "context", "listeners", "history"],
            template=self.language_data.get("intro_template", "Error: intro_template not found.")
        )

        self.metadata_folder = config.get("METADATA_FOLDER", "metadata/prologue/JBFqnCBsd6RMkjVDRZzb")
        self.audio_files = self._load_audio_files()
        self.probability_for_prerecorded = config.get("USE_FILE_PROBABILITY", 0.2)
        self.listeners = self.memory.get_messages('LISTENERS')
        self.context = self.memory.get_messages('AUDIENCE_CONTEXT')

    def _load_language_data(self):
        filepath = self.locales_folder / f"{self.language}.json"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Language file '{filepath}' not found. Using default (English).")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding language file '{filepath}': {e}. Using default (English).")
            return {}

    def _load_audio_files(self):
        audio_files = []
        metadata_path = Path(self.metadata_folder)

        if metadata_path.exists() and metadata_path.is_dir():
            for file in metadata_path.glob("*.mp3"):
                audio_files.append(file)

        print(f"Loaded {len(audio_files)} intro audio files from {self.metadata_folder}")
        return audio_files

    def _get_random_audio_file(self):
        if not self.audio_files:
            return None

        selected_file = random.choice(self.audio_files)

        try:
            with open(selected_file, "rb") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading audio file {selected_file}: {e}")
            return None

    def _generate_prompt(self, song_title, artist, brand, history, processed_context_info, processed_listeners_info):
        return self.intro_prompt_template.format(
            song_title=song_title,
            artist=artist,
            brand=brand,
            history=history,
            context=processed_context_info,
            listeners=processed_listeners_info
        )

    def _preprocess_audience_data(self):
        processed_listeners_info = "our awesome listeners"
        if self.listeners and hasattr(self.listeners[0], 'content'):
            try:
                listeners_dict = json.loads(self.listeners[0].content)
                listener_phrases = []
                for name, details in listeners_dict.items():
                    location = details.get('location')
                    if location:
                        city = location.split(',')[0].strip()
                        listener_phrases.append(f"{name} in {city}")
                    else:
                        listener_phrases.append(name)

                if listener_phrases:
                    if len(listener_phrases) > 1:
                        processed_listeners_info = ", ".join(listener_phrases[:-1]) + " and " + listener_phrases[-1]
                    else:
                        processed_listeners_info = listener_phrases[0]
            except (json.JSONDecodeError, IndexError) as e:
                self.logger.warning(f"Error processing listener data: {e}")

        processed_context_info = "the unique music experience"
        if self.context and hasattr(self.context[0], 'content'):
            try:
                context_dict = json.loads(self.context[0].content)
                description = context_dict.get('description', '')
                if description:
                    processed_context_info = description
            except (json.JSONDecodeError, IndexError) as e:
                self.logger.warning(f"Error processing context data: {e}")

        return processed_listeners_info, processed_context_info

    def create_introduction(self, title, artist, brand):
        self.logger.debug(f"Starting introduction for: {title} by {artist} in {self.language}")

        try:
            if self.audio_files:
                if random.random() < self.probability_for_prerecorded:
                    self.logger.debug(f"Attempting pre-recorded file (probability: {self.probability_for_prerecorded})")
                    audio = self._get_random_audio_file()
                    if audio:
                        self.logger.info("Using pre-recorded audio introduction")
                        return audio
                    self.logger.warning("Pre-recorded audio file found but failed to load")

            if not title or title == "Unknown":
                self.logger.debug("Skipping introduction - invalid song title")
                return None

            history = self.memory.get_messages('CONVERSATION_HISTORY')

            processed_listeners_info, processed_context_info = self._preprocess_audience_data()

            self.logger.debug("Generating LLM introduction")
            prompt = self._generate_prompt(title, artist, brand, history, processed_context_info,
                                           processed_listeners_info)
            print(f"prompt: {prompt}")
            response = self.llm.invoke(prompt)

            if not response:
                self.logger.error("Empty response from LLM")
                return None

            if not hasattr(response, 'content'):
                self.logger.error(f"Malformed LLM response: {type(response)}")
                return None

            tts_text = response.content.split("{")[0].strip()
            self.logger.debug(f"Generated introduction text: {tts_text[:100]}...")
            print(f"tts text: {tts_text}")

            self.logger.debug("Calling ElevenLabs TTS API")

            audio = self.client.text_to_speech.convert(
                voice_id="nPczCjzI2devNBz1zQrb",
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            self.logger.info("Successfully generated TTS introduction")
            return b''.join(audio)

        except Exception as e:
            self.logger.exception(f"Failed to create introduction: {str(e)}")
            return None