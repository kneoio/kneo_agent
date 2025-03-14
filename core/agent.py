#!/usr/bin/env python3
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import importlib

from anthropic import AsyncAnthropic

from api.brand_api import BrandAPI
from core.tool_registry import ToolRegistry
from core.brand_context import BrandContextManager


class DJAgent:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.claude = AsyncAnthropic(api_key=config["claude"]["api_key"])
        self.brand_manager = BrandContextManager()
        self._initialize_brands()
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _initialize_brands(self):
        brand_api = BrandAPI(self.config.get("api", {}))
        brands = brand_api.get_all_brands()
        for brand in brands:
            brand_id = brand.get("id")
            if brand_id:
                self.brand_manager.add_brand(brand_id, brand)

        brand_ids = self.brand_manager.get_all_brand_ids()
        self.logger.info(f"Initialized {len(brand_ids)} brands from API")

    def _register_tools(self):
        """Register all available tools from configuration."""
        for tool_config in self.config.get("tools", []):
            try:
                # Dynamically import the tool class
                module_path = tool_config["module"]
                class_name = tool_config["class"]
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)

                # Add the brand manager to the tool config
                tool_config_with_brands = tool_config.get("config", {}).copy()
                tool_config_with_brands["brand_manager"] = self.brand_manager

                # Instantiate and register the tool
                tool_instance = tool_class(tool_config_with_brands)
                self.tool_registry.register_tool(tool_instance)
                self.logger.info(f"Registered tool: {tool_instance.name}")

            except (ImportError, AttributeError, KeyError) as e:
                self.logger.error(f"Failed to register tool {tool_config.get('name', 'unknown')}: {e}")

    async def _get_claude_response(self, prompt: str, brand_id: str = None) -> str:
        """Get a response from Claude based on the current context."""
        system_prompt = self._build_system_prompt(brand_id)
        try:
            response = await self.claude.messages.create(
                model=self.config["claude"]["model"],
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config["claude"].get("max_tokens", 1000),
                temperature=self.config["claude"].get("temperature", 0.7),
            )
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Error getting response from Claude: {e}")
            return "I'm having trouble connecting to my reasoning system. Let me try again in a moment."

    def _build_system_prompt(self, brand_id: str = None) -> str:
        """Build a system prompt for Claude based on current context and environment."""
        brand = self.brand_manager.get_brand(brand_id)
        if not brand:
            self.logger.error(f"Cannot build prompt: brand {brand_id} not found")
            return "You are an AI DJ Agent. Please help manage music and announcements."

        brand_id = brand.brand_id
        profile_name = brand.get_current_profile()
        state = brand.get_state()

        # Get profile info from the environment profiles tool
        env_profiles = self.tool_registry.get_tool("environment_profiles")
        if env_profiles:
            profile_text = env_profiles.get_profile_guidelines(profile_name)
            profile_obj = env_profiles.get_profile(profile_name)
        else:
            profile_text = f"Profile: {profile_name}"
            profile_obj = {"language": "en"}

        # Get language from profile
        language = profile_obj.get("language", "en") if profile_obj else "en"

        # Build comprehensive system prompt
        prompt = f"""You are an AI DJ Agent for {brand_id} radiostation in a {profile_name} environment.
    Please respond in {language} language.

    Current context:
    - Brand: {brand_id}
    - Environment: {profile_name}
    - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    - Current Song: {state.get('current_song', 'None')}
    - Audience: {state.get('audience_info', {})}
    - Current/Upcoming Events: {state.get('upcoming_events', [])}

    Environment profile guidelines:
    {profile_text}

    Your available tools:
    {self.tool_registry.get_tool_descriptions()}

    When deciding what to do next, consider:
    1. The current context and environment
    2. Appropriate music selection
    3. Engaging commentary that's suitable for the audience
    4. Timing of announcements and transitions
    5. Response to audience feedback and requests

    Maintain an engaging, appropriate tone for the {profile_name} setting.
    """
        return prompt

    async def process_cycle(self, brand_id: str = None):
        """Process a single operation cycle for a specific brand."""
        brand = self.brand_manager.get_brand(brand_id)
        if not brand:
            self.logger.error(f"Cannot process cycle: brand {brand_id} not found")
            return

        # Get current state information
        current_state = brand.get_state()

        # Ask Claude for decision on what to do next
        prompt = f"""
            Current state for brand {brand.brand_id}:
            {current_state}

            What action should I take next? Choose from:
            1. Select and play a new song
            2. Make an announcement
            3. Check for audience feedback
            4. Process a special request
            5. Check for upcoming events
            6. Other (specify)

            Explain your decision briefly and provide necessary details for execution.
        """

        decision = await self._get_claude_response(prompt, brand.brand_id)
        self.logger.info(f"Brand {brand.brand_id} - Claude decision: {decision}")

        # Parse and execute the decision
        await self._execute_decision(decision, brand.brand_id)

        # Update system state after action
        brand.update_state("last_action", decision)

    async def _execute_decision(self, decision: str, brand_id: str = None):
        """Execute the decision made by Claude for a specific brand."""
        brand = self.brand_manager.get_brand(brand_id)
        if not brand:
            self.logger.error(f"Cannot execute decision: brand {brand_id} not found")
            return

        # Simple parsing of the decision text to determine the action
        decision_lower = decision.lower()

        if "play a new song" in decision_lower or "select a song" in decision_lower:
            await self._select_and_play_song(decision, brand.brand_id)
        elif "announcement" in decision_lower or "introduce" in decision_lower:
            await self._make_announcement(decision, brand.brand_id)
        elif "audience feedback" in decision_lower or "check feedback" in decision_lower:
            await self._check_audience_feedback(brand.brand_id)
        elif "special request" in decision_lower or "process request" in decision_lower:
            await self._process_special_request(decision, brand.brand_id)
        elif "upcoming events" in decision_lower or "check events" in decision_lower:
            await self._check_upcoming_events(brand.brand_id)
        else:
            # Generic handling for other types of decisions
            self.logger.info(f"Brand {brand.brand_id} - Executing general decision: {decision}")

    async def _select_and_play_song(self, decision: str, brand_id: str):
        """Select and play a song based on the decision for a specific brand."""
        music_db = self.tool_registry.get_tool("music_database")
        queue_mgr = self.tool_registry.get_tool("song_queue_manager")

        if not music_db or not queue_mgr:
            self.logger.error(f"Brand {brand_id} - Required tools not available for song selection")
            return

        # Extract criteria from decision
        criteria = {"brand_id": brand_id}
        if "genre" in decision.lower():
            genre_start = decision.lower().find("genre") + 5
            genre_end = decision.find(".", genre_start)
            if genre_end == -1:
                genre_end = len(decision)
            genre = decision[genre_start:genre_end].strip()
            criteria["genre"] = genre

        # Query music database for song recommendations
        songs = music_db.search_songs(criteria)
        if songs:
            selected_song = songs[0]  # Take first recommendation for simplicity
            queue_mgr.add_song(selected_song, brand_id=brand_id)
            self.logger.info(
                f"Brand {brand_id} - Added song to queue: {selected_song['title']} by {selected_song['artist']}")

            # Generate introduction for the song
            speech_tool = self.tool_registry.get_tool("speech_generator")
            if speech_tool:
                intro_text = f"Next up, we have {selected_song['title']} by {selected_song['artist']}."
                speech_tool.generate_speech(intro_text, brand_id=brand_id)

            # Update brand context with current song
            brand = self.brand_manager.get_brand(brand_id)
            if brand:
                brand.update_state("current_song", selected_song)

    async def _make_announcement(self, decision: str, brand_id: str):
        """Make an announcement based on the decision for a specific brand."""
        speech_tool = self.tool_registry.get_tool("speech_generator")
        if not speech_tool:
            self.logger.error(f"Brand {brand_id} - Speech generator tool not available")
            return

        # Extract announcement text from decision
        announcement_text = decision
        if "announce that" in decision.lower():
            start_idx = decision.lower().find("announce that") + 13
            announcement_text = decision[start_idx:].strip()

        speech_tool.generate_speech(announcement_text, brand_id=brand_id)
        self.logger.info(f"Brand {brand_id} - Made announcement: {announcement_text}")

    async def _check_audience_feedback(self, brand_id: str):
        """Check for audience feedback for a specific brand."""
        engagement_tool = self.tool_registry.get_tool("audience_engagement")
        if not engagement_tool:
            self.logger.error(f"Brand {brand_id} - Audience engagement tool not available")
            return

        feedback = engagement_tool.get_recent_feedback(brand_id=brand_id)
        if feedback:
            self.logger.info(f"Brand {brand_id} - Received audience feedback: {feedback}")

            # Update brand context with feedback
            brand = self.brand_manager.get_brand(brand_id)
            if brand:
                brand.update_state("feedback", feedback)

            # Ask Claude how to respond to the feedback
            prompt = f"Audience feedback received: {feedback}. How should I respond to this feedback?"
            response_decision = await self._get_claude_response(prompt, brand_id)

            # Execute the response decision
            await self._execute_decision(response_decision, brand_id)

    async def _process_special_request(self, decision: str, brand_id: str):
        """Process a special request for a specific brand."""
        self.logger.info(f"Brand {brand_id} - Processing special request: {decision}")

        if "song request" in decision.lower():
            song_recog = self.tool_registry.get_tool("song_recognition")
            queue_mgr = self.tool_registry.get_tool("song_queue_manager")

            if song_recog and queue_mgr:
                request_details = decision[decision.lower().find("song request") + 12:].strip()
                song_info = song_recog.identify_song(request_details, brand_id=brand_id)
                if song_info:
                    queue_mgr.add_song(song_info, brand_id=brand_id)
                    self.logger.info(f"Brand {brand_id} - Added requested song: {song_info.get('title')}")

    async def _check_upcoming_events(self, brand_id: str):
        """Check for upcoming events for a specific brand."""
        calendar_tool = self.tool_registry.get_tool("event_calendar")
        if not calendar_tool:
            self.logger.error(f"Brand {brand_id} - Event calendar tool not available")
            return

        upcoming_events = calendar_tool.get_upcoming_events(brand_id=brand_id, time_window_minutes=30)
        if upcoming_events:
            self.logger.info(f"Brand {brand_id} - Upcoming events: {upcoming_events}")

            # Update brand context with events
            brand = self.brand_manager.get_brand(brand_id)
            if brand:
                brand.update_state("upcoming_events", upcoming_events)

            # Ask Claude how to prepare for the upcoming event
            event_str = ", ".join([f"{e['title']} at {e['time']}" for e in upcoming_events])
            prompt = f"Upcoming events: {event_str}. How should I prepare for these events?"
            prep_decision = await self._get_claude_response(prompt, brand_id)

            # Execute the preparation decision
            await self._execute_decision(prep_decision, brand_id)

    async def run_async(self, duration_seconds=None):
        """Run the DJ Agent asynchronously for all brands."""
        self.logger.info("Starting DJ Agent async operation for all brands")
        start_time = time.time()

        while True:
            try:
                # Check if duration limit is reached
                if duration_seconds and (time.time() - start_time > duration_seconds):
                    self.logger.info(f"Reached time limit of {duration_seconds} seconds")
                    break

                # Process cycle for each brand
                for brand_id in self.brand_manager.get_all_brand_ids():
                    await self.process_cycle(brand_id)

                # Sleep between cycles
                await asyncio.sleep(self.config.get("cycle_interval_seconds", 10))
            except Exception as e:
                self.logger.error(f"Error in process cycle: {e}")
                await asyncio.sleep(self.config.get("error_retry_seconds", 30))

    def run(self, duration_seconds=None):
        """Run the DJ Agent in a blocking manner."""
        self.logger.info("Starting DJ Agent operation")
        asyncio.run(self.run_async(duration_seconds))
