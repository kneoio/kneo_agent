import json
import logging
import random
from typing import Dict, Any, List

from langchain_anthropic import ChatAnthropic


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
