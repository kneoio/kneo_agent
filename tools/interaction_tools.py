# tools/interaction_tools.py

import json
import logging
import random
from pathlib import Path

from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from api.interaction_memory import InteractionMemory


class InteractionTool:
    def __init__(self, config, memory: InteractionMemory, language="en", agent_config=None, radio_station_name=None):
        self.logger = logging.getLogger(__name__)
        self.llm = ChatAnthropic(
            model_name=config.get("claude").get("model"),
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.ttsClient = ElevenLabs(
            api_key=config.get("elevenlabs").get("api_key")
        )

        self.memory = memory
        self.language = language
        self.agent_config = agent_config
        self.radio_station_name = radio_station_name
        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist", "brand", "context", "listeners", "history", "instant_message"],
            template=self.agent_config["mainPrompt"]
        )

        self.metadata_folder = Path("metadata") / self.radio_station_name
        self.metadata_folder.mkdir(parents=True, exist_ok=True)

        self.audio_files = self._load_audio_files()
        talkativity_value = self.agent_config.get("talkativity")
        self.logger.info(f"Agent talkativity from agent_config: {self.agent_config.get('talkativity')}")
        if isinstance(talkativity_value, (int, float)):
            self.probability_for_prerecorded = 1.0 - talkativity_value
        else:
            self.logger.warning(f"Invalid or missing 'talkativity' ({talkativity_value}), defaulting pre-recorded probability to 0.5 (50% chance)")
            self.probability_for_prerecorded = 0.5

    def _load_audio_files(self):
        audio_files = []
        if self.metadata_folder.exists() and self.metadata_folder.is_dir():
            for file in self.metadata_folder.glob("*.mp3"):
                audio_files.append(file)

        if not audio_files and self.agent_config.get('fillers'):
            self.logger.info(f"No audio files found for {self.radio_station_name}. Generating fillers...")
            self._generate_filler_files()
            # Reload after generation
            for file in self.metadata_folder.glob("*.mp3"):
                audio_files.append(file)

        self.logger.info(f"Loaded {len(audio_files)} intro audio files from {self.metadata_folder}")
        return audio_files

    def _generate_filler_files(self):
        fillers = self.agent_config.get('fillers', [])

        if not fillers:
            self.logger.warning("No fillers found in agent configuration")
            return

        self.logger.info(f"Generating {len(fillers)} filler files for {self.radio_station_name}")

        for i, filler_prompt in enumerate(fillers):
            try:
                file_name = self.metadata_folder / f"filler_{i + 1:02d}.mp3"
                if file_name.exists():
                    self.logger.debug(f"Filler file {file_name} already exists, skipping")
                    continue

                self.logger.debug(f"Generating filler {i + 1}/{len(fillers)}: {filler_prompt}")
                effect = self.ttsClient.text_to_sound_effects.convert(
                    text=filler_prompt,
                )
                with open(file_name, "wb") as f:
                    for chunk in effect:
                        f.write(chunk)

                self.logger.info(f"Generated filler audio: {file_name}")

            except Exception as e:
                self.logger.error(f"Failed to generate filler {i + 1} ({filler_prompt}): {str(e)}")
                continue

        self.logger.info(f"Finished generating filler files for {self.radio_station_name}")

    def _get_random_audio_file(self):
        if not self.audio_files:
            return None
        selected_file = random.choice(self.audio_files)

        try:
            with open(selected_file, "rb") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading audio file {selected_file}: {e}")
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
                        return audio, "Used pre-recorded audio"
                    self.logger.warning("Pre-recorded audio file found but failed to load, attempting TTS.")

            if not title or title == "Unknown":
                reason = "Skipped: Invalid song title"
                self.logger.debug(reason)
                return None, reason

            # Get all memory data in a single request
            memory_data = self.memory.get_all_memory_data()
            
            # Extract data from the response
            instant_message = memory_data.get('message', {})
            history_messages = memory_data.get('introductions', [])
            listeners = memory_data.get('listeners', [])
            environment = memory_data.get('environment', [])
            
            # Log the data being used
            print(f"=== PROMPT VARIABLES ===")
            print(f"song_title: {title}")
            print(f"artist: {artist}")
            print(f"brand: {brand}")
            print(f"history: {history_messages}")
            print(f"environment: {environment}")
            print(f"listeners: {listeners}")
            print(f"instant_message: {instant_message}")
            print(f"=== END PROMPT VARIABLES ===")

            prompt = self.intro_prompt_template.format(
                song_title=title,
                artist=artist,
                brand=brand,
                history=json.dumps(history_messages),
                context=json.dumps(environment),
                listeners=json.dumps(listeners),
                instant_message=json.dumps(instant_message)
            )

            self.logger.debug(f"Generated prompt: {prompt}")

            response = self.llm.invoke(prompt)

            if not response:
                reason = "Skipped: Empty response from LLM"
                self.logger.error(reason)
                return None, reason

            if not hasattr(response, 'content'):
                reason = f"Skipped: Malformed LLM response (type: {type(response)})"
                self.logger.error(reason)
                return None, reason

            tts_text = response.content.split("{")[0].strip()
            
            if not tts_text:
                reason = "Skipped: LLM generated empty text for TTS"
                self.logger.warning(reason)
                return None, reason

            self.logger.debug(f"Generated introduction text: {tts_text[:100]}...")
            self.logger.debug(f"TTS text: {tts_text}")

            self._save_introduction_to_history(title, artist, tts_text)
            self.logger.debug("Calling ElevenLabs TTS API")

            voice_id = current_agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')

            audio_stream = self.ttsClient.text_to_speech.convert( # Renamed 'audio' to 'audio_stream' to avoid confusion before join
                voice_id=voice_id,
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            final_audio = b''.join(audio_stream) # Join the stream into bytes

            if not final_audio: # Check if TTS returned empty audio
                reason = "Skipped: TTS conversion resulted in empty audio"
                self.logger.warning(reason)
                return None, reason

            reason = f"Successfully generated TTS introduction using voice: {voice_id}"
            self.logger.info(reason)
            return final_audio, reason

        except Exception as e:
            reason = f"Skipped: Failed to create introduction due to an exception: {str(e)}"
            self.logger.exception(reason) # Use .exception to include stack trace
            return None, reason