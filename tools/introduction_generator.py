import json
import logging
from typing import Dict, Any

from langchain_anthropic import ChatAnthropic


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
