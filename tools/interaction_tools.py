# tools/interaction_tools.py
import json
import logging
import random
from pathlib import Path

from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from api.interaction_memory import InteractionMemory
from tools.filler_generator import FillerGenerator


class InteractionTool:
    def __init__(self, config, memory: InteractionMemory, language="en", agent_config=None, radio_station_name=None):
        self.logger = logging.getLogger(__name__)

        self.ai_logger = logging.getLogger('tools.interaction_tools.ai')

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
        self.ai_dj_name = self.agent_config["name"]
        self.radio_station_name = radio_station_name
        self.intro_prompt_template = PromptTemplate(
            input_variables=["ai_dj_name", "song_title", "artist", "brand", "context", "listeners", "history",
                             "instant_message", "events"],
            template=self.agent_config["prompt"]
        )

        self.metadata_folder = Path("metadata") / self.radio_station_name
        self.filler_generator = FillerGenerator(self.ttsClient, self.metadata_folder)

        self.audio_files = self._load_audio_files()
        talkativity_value = self.agent_config.get("talkativity")
        self.logger.info(f"Agent talkativity from agent_config: {self.agent_config.get('talkativity')}")
        if isinstance(talkativity_value, (int, float)):
            self.probability_for_prerecorded = 1.0 - talkativity_value
        else:
            self.logger.warning(
                f"Invalid or missing 'talkativity' ({talkativity_value}), defaulting pre-recorded probability to 0.5 (50% chance)")
            self.probability_for_prerecorded = 0.5

    def _load_audio_files(self):
        audio_files = self.filler_generator.load_audio_files()

        if not audio_files and self.agent_config.get('fillers'):
            self.logger.info(f"No audio files found for {self.radio_station_name}. Generating fillers...")
            self.filler_generator.generate_filler_files(self.agent_config.get('fillers'))
            audio_files = self.filler_generator.load_audio_files()

        return audio_files

    def _get_random_prerecorded(self):
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
                    audio = self._get_random_prerecorded()
                    if audio:
                        self.logger.info("Using pre-recorded audio introduction")
                        return audio, "Used pre-recorded audio"
                    self.logger.warning("Pre-recorded audio file found but failed to load, attempting TTS.")

            if not title or title == "Unknown":
                reason = "Skipped: Invalid song title"
                self.logger.debug(reason)
                return None, reason

            memory_data = self.memory.get_all_memory_data()
            instant_message = memory_data.get('messages', [])
            history_messages = memory_data.get('history', [])
            listeners = memory_data.get('listeners', [])
            environment = memory_data.get('environment', [])
            events = memory_data.get('events', [])
            event_ids = memory_data.get('event_ids', [])

            print(f"=== PROMPT VARIABLES ===")
            print(f"ai_dj_name: {self.ai_dj_name}")
            print(f"song_title: {title}")
            print(f"artist: {artist}")
            print(f"brand: {brand}")
            print(f"history: {history_messages}")
            print(f"environment: {environment}")
            print(f"listeners: {listeners}")
            print(f"instant_message: {instant_message}")
            print(f"events: {events}")
            print(f"=== END PROMPT VARIABLES ===")
            prompt = self.intro_prompt_template.format(
                ai_dj_name=self.ai_dj_name,
                song_title=title,
                artist=artist,
                brand=brand,
                context=json.dumps(environment),
                listeners=json.dumps(listeners),
                history=json.dumps(history_messages),
                instant_message=json.dumps(instant_message),
                events=json.dumps(events)
            )

            self.ai_logger.info(f"PROMPT for '{title}' by {artist}:\n{prompt}\n{'=' * 80}")
            response = self.llm.invoke(prompt)
            if instant_message:
                self.logger.info("Instant message was used in prompt, resetting instant messages")
                reset_result = self.memory.reset_messages()
                self.logger.debug(f"Reset instant messages result: {reset_result}")

            if events and event_ids:
                self.logger.info(f"Events were used in prompt, resetting {len(event_ids)} specific events")
                for event_id in event_ids:
                    reset_result = self.memory.reset_event_by_id(event_id)
                    self.logger.debug(f"Reset event {event_id} result: {reset_result}")

            if not response:
                reason = "Skipped: Empty response from LLM"
                self.logger.error(reason)
                return None, reason

            if not hasattr(response, 'content'):
                reason = f"Skipped: Malformed LLM response (type: {type(response)})"
                self.logger.error(reason)
                return None, reason

            # Log the complete AI response
            self.ai_logger.info(f"AI RESPONSE for '{title}' by {artist}:\n{response.content}\n{'-' * 80}")

            tts_text = response.content.split("{")[0].strip()

            # Log the processed TTS text
            self.ai_logger.info(f"PROCESSED TTS TEXT for '{title}' by {artist}:\n{tts_text}\n{'*' * 80}\n")

            if not tts_text:
                reason = "Skipped: LLM generated empty text for TTS"
                self.logger.warning(reason)
                return None, reason

            if "copyright" in tts_text.lower():
                reason = "TTS text contains copyright-related content, using pre-recorded audio instead"
                self.logger.warning(reason)
                audio = self._get_random_prerecorded()
                if audio:
                    self.logger.info("Using pre-recorded audio due to copyright content")
                    return audio, reason
                else:
                    reason = "Skipped: TTS text contains copyright-related content and no pre-recorded audio available"
                    self.logger.warning(reason)
                    return None, reason

            self.logger.debug(f"Generated introduction text: {tts_text[:100]}...")

            self._save_introduction_to_history(title, artist, tts_text)
            self.logger.debug("Calling ElevenLabs TTS API")

            voice_id = current_agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')

            audio_stream = self.ttsClient.text_to_speech.convert(
                voice_id=voice_id,
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            final_audio = b''.join(audio_stream)

            if not final_audio:
                reason = "Skipped: TTS conversion resulted in empty audio"
                self.logger.warning(reason)
                return None, reason

            reason = f"Successfully generated TTS introduction using voice: {voice_id}"
            self.logger.info(reason)
            return final_audio, reason

        except Exception as e:
            reason = f"Skipped: Failed to create introduction due to an exception: {str(e)}"
            self.logger.exception(reason)
            return None, reason