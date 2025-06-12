import json
import logging
import random
from pathlib import Path

from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from api.interaction_memory import InteractionMemory


def _parse_memory_payload(payload):
    if isinstance(payload, list) and len(payload) > 0:
        return payload[0].content
    return payload

class InteractionTool:
    def __init__(self, config, memory: InteractionMemory, language="en", agent_config=None):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.ttsClient = ElevenLabs(
            api_key=config.get("elevenlabs").get("api_key")
        )

        self.memory = memory
        self.language = language
        self.agent_config = agent_config or {}
        self.locales_folder = Path("prompt/interaction")
        self.language_data = self._load_language_data()
        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist", "brand", "context", "listeners", "history"],
            template=self.agent_config.get('mainPrompt',
                                           self.language_data.get("intro_template",
                                                                  "Error: intro_template not found."))
        )

        self.metadata_folder = config.get("METADATA_FOLDER", "metadata/prologue/JBFqnCBsd6RMkjVDRZzb")
        self.audio_files = self._load_audio_files()
        self.probability_for_prerecorded = config.get("USE_FILE_PROBABILITY", 0.3)
        self.listeners = _parse_memory_payload(self.memory.get_messages('LISTENERS'))
        self.context = _parse_memory_payload(self.memory.get_messages('AUDIENCE_CONTEXT'))

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

    def _save_introduction_to_history(self, title, artist, introduction_text):
        try:
            history_entry = {
                "title": title,
                "artist": artist,
                "content": introduction_text
            }

            success = self.memory.store_conversation_history(history_entry)
            if success:
                self.logger.info(f"Successfully saved introduction to history for '{title}' by {artist}")
            else:
                self.logger.warning(f"Failed to save introduction to history for '{title}' by {artist}")

        except Exception as e:
            self.logger.error(f"Error saving introduction to history: {str(e)}")

    def create_introduction(self, title, artist, brand, agent_config=None):
        current_agent_config = agent_config or self.agent_config

        self.logger.debug(f"Starting introduction for: {title} by {artist} in {self.language}")
        if current_agent_config.get('name'):
            self.logger.debug(f"Using agent: {current_agent_config['name']}")

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

            prompt = self.intro_prompt_template.format(
                song_title=title,
                artist=artist,
                brand=brand,
                history=self.memory.get_messages('CONVERSATION_HISTORY'),
                context=self.context,
                listeners=self.listeners
            )

            print(f"generated prompt : {prompt}")

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

            self._save_introduction_to_history(title, artist, tts_text)
            self.logger.debug("Calling ElevenLabs TTS API")

            voice_id = current_agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')

            audio = self.ttsClient.text_to_speech.convert(
                voice_id=voice_id,
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            self.logger.info(f"Successfully generated TTS introduction using voice: {voice_id}")
            return b''.join(audio)

        except Exception as e:
            self.logger.exception(f"Failed to create introduction: {str(e)}")
            return None
