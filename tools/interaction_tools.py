import logging
import os
import random
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain.memory import ConversationBufferMemory

load_dotenv()


class InteractionTool:
    def __init__(self, config, memory: ConversationBufferMemory):
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )

        self.memory = memory

        self.intro_prompt_template = PromptTemplate(
            input_variables=["song_title", "artist", "brand", "context", "listeners", "history"],
            template="""
            You are a radio DJ. Introduce "{song_title}" by {artist}.
            Keep it short (10-30 words). You can mention radio station name: "{brand}".

            Context:
            {context}

            Listeners:
            {listeners}
            
            Previous interactions context:
            {history}
            
            Make sure your introduction flows naturally from previous interactions.
            """
        )

        self.metadata_folder = config.get("METADATA_FOLDER", "metadata/prologue/JBFqnCBsd6RMkjVDRZzb")
        self.audio_files = self._load_audio_files()
        self.use_file_probability = config.get("USE_FILE_PROBABILITY", 0.2)

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

            # Save this interaction to memory
            #self.memory.save_context(
            #    {"input": f"Introducing {title} by {artist} for {brand}"},
            #    {"output": response.content}
            #)

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
                voice_id="onwK4e9ZLuTAKqWW03F9", #Daniel
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