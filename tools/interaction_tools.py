import json
import logging
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from elevenlabs.client import ElevenLabs
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END, MessagesState
from dotenv import load_dotenv

from api.interaction_memory import InteractionMemory
from tools.filler_generator import FillerGenerator

load_dotenv()


class DJState(MessagesState):
    brand: str
    songs: List[Dict[str, Any]]
    selected_song: Dict[str, Any]
    introduction_text: str
    audio_data: Optional[bytes]
    reason: str
    title: str
    artist: str


class MCPMusicCatalog:
    """Handles music catalog operations via MCP"""

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def get_songs(self, brand: str, page: int = 1, size: int = 50) -> List[Dict[str, Any]]:
        """Fetch songs from MCP catalog"""
        if not self.mcp_client:
            self.logger.warning("No MCP client available")
            return []

        try:
            result = await self.mcp_client.call_tool("get_brand_soundfragments", {
                "brand": brand,
                "page": page,
                "size": size
            })
            songs = result.get("fragments", [])
            self.logger.info(f"Fetched {len(songs)} songs for brand {brand}")
            return songs
        except Exception as e:
            self.logger.error(f"Failed to fetch songs: {e}")
            return []

    async def get_song_details(self, song_id: str) -> Dict[str, Any]:
        """Get detailed song information"""
        if not self.mcp_client:
            return {"error": "No MCP client"}

        try:
            result = await self.mcp_client.call_tool("get_song", {"song_id": song_id})
            return {"details": result.content[0].text}
        except Exception as e:
            return {"error": str(e)}


class SongSelector:
    """Handles intelligent song selection using LLM"""

    def __init__(self, llm: ChatAnthropic, ai_dj_name: str):
        self.llm = llm
        self.ai_dj_name = ai_dj_name
        self.logger = logging.getLogger(__name__)

    async def select_song(self, songs: List[Dict[str, Any]], brand: str, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Select best song based on context and memory"""
        if not songs:
            self.logger.warning("No songs available for selection")
            return {}

        # Prepare song options for LLM (limit to 20)
        song_options = self._format_song_options(songs[:20])

        prompt = self._build_selection_prompt(song_options, brand, memory_data)

        try:
            response = await self.llm.ainvoke([("human", prompt)])
            selection = response.content.strip()

            # Parse and validate selection
            song_index = self._parse_selection(selection, len(song_options))
            selected_song = songs[song_index]

            song_info = selected_song.get('soundfragment', {})
            self.logger.info(f"Selected: {song_info.get('title', 'Unknown')} by {song_info.get('artist', 'Unknown')}")

            return selected_song

        except Exception as e:
            self.logger.error(f"Song selection failed: {e}, using random")
            return random.choice(songs)

    def _format_song_options(self, songs: List[Dict[str, Any]]) -> List[str]:
        """Format songs for LLM prompt"""
        options = []
        for i, song in enumerate(songs):
            song_info = song.get('soundfragment', {})
            plays = song.get('playedByBrandCount', 0)
            options.append(
                f"{i}: {song_info.get('title', 'Unknown')} by {song_info.get('artist', 'Unknown')} "
                f"- Genre: {song_info.get('genre', 'Unknown')} - Plays: {plays}"
            )
        return options

    def _build_selection_prompt(self, song_options: List[str], brand: str, memory_data: Dict[str, Any]) -> str:
        """Build prompt for song selection"""
        return f"""You are {self.ai_dj_name}, selecting the perfect song for {brand} radio.

Available songs:
{chr(10).join(song_options)}

Context:
- Recent history: {json.dumps(memory_data.get('history', [])[-5:])}
- Current listeners: {len(memory_data.get('listeners', []))}
- Messages: {json.dumps(memory_data.get('messages', []))}
- Events: {json.dumps(memory_data.get('events', []))}

Consider:
- Avoid recently played songs
- Match listener mood/energy
- Respond to any messages or events
- Create good flow and variety

Respond with only the number (0-{len(song_options) - 1}) of your chosen song."""

    def _parse_selection(self, selection: str, max_index: int) -> int:
        """Parse and validate LLM selection"""
        try:
            song_index = int(selection.strip())
            if 0 <= song_index < max_index:
                return song_index
            else:
                self.logger.warning(f"Invalid song index {song_index}, using random")
                return random.randint(0, max_index - 1)
        except ValueError:
            self.logger.warning(f"Could not parse selection '{selection}', using random")
            return random.randint(0, max_index - 1)


class IntroductionGenerator:
    """Generates song introductions using LLM"""

    def __init__(self, llm: ChatAnthropic, ai_dj_name: str):
        self.llm = llm
        self.ai_dj_name = ai_dj_name
        self.logger = logging.getLogger(__name__)

    async def generate_intro(self, title: str, artist: str, brand: str, memory_data: Dict[str, Any]) -> str:
        """Generate engaging introduction for song"""
        prompt = f"""You are {self.ai_dj_name}, a radio DJ for {brand}.

Create an engaging introduction for this song:
Title: {title}
Artist: {artist}

Context:
- History: {json.dumps(memory_data.get('history', [])[-3:])}
- Current listeners: {len(memory_data.get('listeners', []))}
- Recent messages: {json.dumps(memory_data.get('messages', []))}

Generate a natural, conversational introduction suitable for text-to-speech. 
Keep it under 200 words and avoid copyright content.
Focus on engaging the audience and building excitement for the song."""

        try:
            response = await self.llm.ainvoke([("human", prompt)])
            intro_text = response.content.strip()

            self.logger.info(f"Generated intro for '{title}': {intro_text[:100]}...")
            return intro_text

        except Exception as e:
            self.logger.error(f"Failed to generate intro: {e}")
            return f"Now playing {title} by {artist}"


class AudioProcessor:
    """Handles audio generation and prerecorded files"""

    def __init__(self, tts_client: ElevenLabs, filler_generator: FillerGenerator,
                 agent_config: Dict[str, Any], memory: InteractionMemory):
        self.tts_client = tts_client
        self.filler_generator = filler_generator
        self.agent_config = agent_config
        self.memory = memory
        self.logger = logging.getLogger(__name__)

        # Load prerecorded audio files
        self.audio_files = self._load_audio_files()

        # Calculate probability for prerecorded vs generated content
        talkativity = self.agent_config.get("talkativity", 0.5)
        self.prerecorded_probability = 1.0 - float(talkativity)

    def _load_audio_files(self) -> List[Path]:
        """Load available prerecorded audio files"""
        audio_files = self.filler_generator.load_audio_files()
        if not audio_files and self.agent_config.get('fillers'):
            self.logger.info("Generating filler files...")
            self.filler_generator.generate_filler_files(self.agent_config.get('fillers'))
            audio_files = self.filler_generator.load_audio_files()
        return audio_files

    def should_use_prerecorded(self) -> bool:
        """Decide whether to use prerecorded audio"""
        return self.audio_files and random.random() < self.prerecorded_probability

    async def get_prerecorded_audio(self) -> Tuple[Optional[bytes], str]:
        """Get prerecorded audio data"""
        if not self.audio_files:
            return None, "No prerecorded files available"

        try:
            selected_file = random.choice(self.audio_files)
            with open(selected_file, "rb") as f:
                audio_data = f.read()

            self.logger.info(f"Using prerecorded audio: {selected_file}")
            return audio_data, "Used pre-recorded audio"

        except Exception as e:
            self.logger.error(f"Error reading audio file: {e}")
            return None, f"Failed to load prerecorded: {e}"

    async def generate_tts_audio(self, text: str, title: str, artist: str) -> Tuple[Optional[bytes], str]:
        """Generate TTS audio from text"""
        if not text:
            return None, "No text provided for TTS"

        # Check for copyright content
        if "copyright" in text.lower():
            self.logger.warning("Copyright content detected")
            return await self.get_prerecorded_audio()

        try:
            # Save to history
            self._save_to_history(title, artist, text)

            # Generate TTS
            voice_id = self.agent_config.get('preferredVoice', 'nPczCjzI2devNBz1zQrb')
            audio_stream = self.tts_client.text_to_speech.convert(
                voice_id=voice_id,
                text=text[:500],  # Limit text length
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            audio_data = b''.join(audio_stream)

            if audio_data:
                self.logger.info("TTS generation successful")
                return audio_data, f"Generated TTS using voice: {voice_id}"
            else:
                return None, "TTS conversion resulted in empty audio"

        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}")
            return None, f"TTS generation failed: {str(e)}"

    def _save_to_history(self, title: str, artist: str, text: str):
        """Save introduction to conversation history"""
        try:
            history_entry = {
                "title": title,
                "artist": artist,
                "content": text
            }
            success = self.memory.store_conversation_history(history_entry)
            if success:
                self.logger.info(f"Saved to history: '{title}' by {artist}")
            else:
                self.logger.warning("Failed to save to history")
        except Exception as e:
            self.logger.error(f"Error saving to history: {e}")


class RadioDJAgent:
    """Main Radio DJ Agent orchestrating the workflow"""

    def __init__(self, config, memory: InteractionMemory, language="en",
                 agent_config=None, radio_station_name=None, mcp_client=None):
        self.logger = logging.getLogger(__name__)

        # Initialize LLM
        self.llm = ChatAnthropic(
            model_name=config.get("claude").get("model"),
            temperature=0.7,
            api_key=config.get("claude").get("api_key")
        )

        # Initialize components
        self.memory = memory
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.radio_station_name = radio_station_name

        # Initialize specialized components
        self.music_catalog = MCPMusicCatalog(mcp_client)
        self.song_selector = SongSelector(self.llm, self.ai_dj_name)
        self.intro_generator = IntroductionGenerator(self.llm, self.ai_dj_name)

        # Initialize audio processor
        metadata_folder = Path("metadata") / self.radio_station_name
        filler_generator = FillerGenerator(
            ElevenLabs(api_key=config.get("elevenlabs").get("api_key")),
            metadata_folder
        )
        self.audio_processor = AudioProcessor(
            ElevenLabs(api_key=config.get("elevenlabs").get("api_key")),
            filler_generator,
            self.agent_config,
            memory
        )

        # Build workflow graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the workflow graph"""
        workflow = StateGraph(state_schema=DJState)

        # Add nodes
        workflow.add_node("check_prerecorded", self._check_prerecorded)
        workflow.add_node("fetch_songs", self._fetch_songs)
        workflow.add_node("select_song", self._select_song)
        workflow.add_node("generate_intro", self._generate_intro)
        workflow.add_node("create_audio", self._create_audio)
        workflow.add_node("use_prerecorded", self._use_prerecorded)

        # Set entry point
        workflow.set_entry_point("check_prerecorded")

        # Add conditional edges
        workflow.add_conditional_edges(
            "check_prerecorded",
            self._should_use_prerecorded,
            {
                "prerecorded": "use_prerecorded",
                "generate": "fetch_songs"  # Always fetch songs now
            }
        )

        # Add linear flow for song processing
        workflow.add_edge("fetch_songs", "select_song")
        workflow.add_edge("select_song", "generate_intro")
        workflow.add_edge("generate_intro", "create_audio")

        # End nodes
        workflow.add_edge("create_audio", END)
        workflow.add_edge("use_prerecorded", END)

        return workflow.compile()

    async def _check_prerecorded(self, state: DJState) -> DJState:
        """Check if prerecorded audio should be used"""
        state["reason"] = "Checking prerecorded options"
        return state

    def _should_use_prerecorded(self, state: DJState) -> str:
        """Decide between prerecorded and generated content"""
        if self.audio_processor.should_use_prerecorded():
            return "prerecorded"
        return "generate"

    async def _use_prerecorded(self, state: DJState) -> DJState:
        """Use prerecorded audio"""
        audio_data, reason = await self.audio_processor.get_prerecorded_audio()

        state["audio_data"] = audio_data
        state["reason"] = reason
        state["title"] = "Unknown"
        state["artist"] = "Unknown"

        return state

    async def _fetch_songs(self, state: DJState) -> DJState:
        """Fetch songs from music catalog"""
        songs = await self.music_catalog.get_songs(state["brand"])
        state["songs"] = songs

        if not songs:
            state["reason"] = "No songs available from catalog"

        return state

    async def _select_song(self, state: DJState) -> DJState:
        """Select best song from catalog"""
        if not state["songs"]:
            state["selected_song"] = {}
            state["reason"] = "No songs to select from"
            state["title"] = "Unknown"
            state["artist"] = "Unknown"
            return state

        # Get memory context
        memory_data = self.memory.get_all_memory_data()

        # Select song using LLM
        selected_song = await self.song_selector.select_song(
            state["songs"],
            state["brand"],
            memory_data
        )

        state["selected_song"] = selected_song

        # Extract song info
        song_info = selected_song.get('soundfragment', {})
        state["title"] = song_info.get('title', 'Unknown')
        state["artist"] = song_info.get('artist', 'Unknown')

        return state

    async def _generate_intro(self, state: DJState) -> DJState:
        """Generate introduction text"""
        memory_data = self.memory.get_all_memory_data()

        intro_text = await self.intro_generator.generate_intro(
            state["title"],
            state["artist"],
            state["brand"],
            memory_data
        )

        state["introduction_text"] = intro_text
        return state

    async def _create_audio(self, state: DJState) -> DJState:
        """Create final audio from introduction text"""
        audio_data, reason = await self.audio_processor.generate_tts_audio(
            state["introduction_text"],
            state["title"],
            state["artist"]
        )

        state["audio_data"] = audio_data
        state["reason"] = reason

        return state

    async def create_introduction(self, brand: str, agent_config=None) -> Tuple[Optional[bytes], str, str, str]:
        """Main entry point for creating radio introduction"""
        # Reset memory events and messages
        self._reset_memory()

        # Initial state
        initial_state = {
            "messages": [],
            "brand": brand,
            "songs": [],
            "selected_song": {},
            "introduction_text": "",
            "audio_data": None,
            "reason": "",
            "title": "Unknown",
            "artist": "Unknown"
        }

        try:
            # Execute workflow
            result = await self.graph.ainvoke(initial_state)

            return (
                result["audio_data"],
                result["reason"],
                result["title"],
                result["artist"]
            )

        except Exception as e:
            reason = f"Workflow execution failed: {str(e)}"
            self.logger.exception(reason)
            return None, reason, "Unknown", "Unknown"

    def _reset_memory(self):
        """Reset temporary memory data"""
        memory_data = self.memory.get_all_memory_data()

        # Reset instant messages
        if memory_data.get('messages'):
            self.logger.info("Resetting instant messages")
            self.memory.reset_messages()

        # Reset events
        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])
        if events and event_ids:
            self.logger.info(f"Resetting {len(event_ids)} events")
            for event_id in event_ids:
                self.memory.reset_event_by_id(event_id)