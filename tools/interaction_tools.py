import json
import logging
import random
from pathlib import Path

from elevenlabs.client import ElevenLabs
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic


class InteractionTool:
    def __init__(self, config, memory: ConversationBufferMemory, language="en"):
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        self.client = ElevenLabs(
            api_key = config.get("elevenlabs").get("api_key")
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
        self.use_file_probability = config.get("USE_FILE_PROBABILITY", 0.2)

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

    def create_introduction(self, title, artist, brand):
        logger = logging.getLogger(__name__)

        try:
            logger.debug(f"Starting introduction for: {title} by {artist} in {self.language}")

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

            # Get conversation history from memory
            listeners = self.memory.load_memory_variables({}).get('listeners', '')
            context = self.memory.load_memory_variables({}).get('context', '')
            history = self.memory.load_memory_variables({}).get('history', '')

            # 3. Generate text
            logger.debug("Generating LLM introduction")
            prompt = self.intro_prompt_template.format(
                song_title=title,
                artist=artist,
                brand=brand,
                history=history,
                context=context,
                listeners=listeners
            )
            response = self.llm.invoke(prompt)

            # Save this interaction to memory (consider if you need to adapt for language)
            # self.memory.save_context(
            #     {"input": f"Introducing {title} by {artist} for {brand} in {self.language}"},
            #     {"output": response.content}
            # )

            # 4. Extract clean content
            if not response:
                logger.error("Empty response from LLM")
                return None

            if not hasattr(response, 'content'):
                logger.error(f"Malformed LLM response: {type(response)}")
                return None

            tts_text = response.content.split("{")[0].strip()
            logger.debug(f"Generated introduction text: {tts_text[:100]}...")

            # 5. Generate TTS (consider using language-specific voices if available)
            logger.debug("Calling ElevenLabs TTS API")

            audio = self.client.text_to_speech.convert(
                #voice_id="JBFqnCBsd6RMkjVDRZzb",
                #voice_id="9BWtsMINqrJLrRacOk9x", #Aria
                #voice_id="CwhRBWXzGAHq8TQ4Fs17", #Roger 1
                #voice_id="IKne3meq5aSn9XLyUdCD", #Charlie
                #voice_id="JBFqnCBsd6RMkjVDRZzb", #George
                #voice_id=" N2lVS1w4EtoT3dr4eOWO", #Callum
                #voice_id="SAz9YHcvj6GT2YYXdXww", #River  clean woman
                #voice_id="TX3LPaxmHKxFdv7VOQHJ", #Liam 2
                #voice_id="XB0fDUnXU5powFXDhCwa", #Charlotte 6
                #voice_id="bIHbv24MWmeRgasZH58o", #Will
                #voice_id="cjVigY5qzO86Huf0OWal", #Eric 2
                #voice_id="iP95p4xoKVk53GoZ742B", #Chris 2
                #voice_id="nPczCjzI2devNBz1zQrb", #Brian 1
                #voice_id="onwK4e9ZLuTAKqWW03F9", #Daniel
                #voice_id="aLFUti4k8YKvtQGXv0UO", #Paulo
                voice_id="l88WmPeLH7L0O0VA9lqm", #Lax
                text=tts_text[:500],
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            logger.info("Successfully generated TTS introduction")
            return b''.join(audio)

        except Exception as e:
            logger.exception(f"Failed to create introduction: {str(e)}")
            return None

        #- Sarah: EXAVITQu4vr4xnSDxMaL
        #- Laura: FGY2WhTYpPnrIDTdsKH5
        #- Charlie: IKne3meq5aSn9XLyUdCD
        #- George: JBFqnCBsd6RMkjVDRZzb
        #- Callum: N2lVS1w4EtoT3dr4eOWO
        #- River: SAz9YHcvj6GT2YYXdXww
        #- Liam: TX3LPaxmHKxFdv7VOQHJ
        #- Charlotte: XB0fDUnXU5powFXDhCwa
        #- Alice: Xb7hH8MSUJpSbSDYk0k2
        #- Matilda: XrExE9yKIg1WjnnlVkGX
        #- Will: bIHbv24MWmeRgasZH58o
        #- Jessica: cgSgspJ2msm6clMCkdW9
        #- Eric: cjVigY5qzO86Huf0OWal
        #- Chris: iP95p4xoKVk53GoZ742B
        #- Brian: nPczCjzI2devNBz1zQrb
        #- Daniel: onwK4e9ZLuTAKqWW03F9
        #- Lily: pFZP5JQG7iQjIQuC4Bku
        #- Bill: pqHfZKP75CvOlQylNhV4
        #- Grandpa  Spuds Oxley: NOpBlnGInO9m6vDvFkFC
        #- Paulo PT: aLFUti4k8YKvtQGXv0UO
        #- Lax2: l88WmPeLH7L0O0VA9lqm