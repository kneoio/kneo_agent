#!/usr/bin/env python3
import logging
from typing import Callable, Awaitable, Dict, Any


class DecisionExecutor:
    def __init__(self, brand_manager, tool_registry, claude_response_func):
        self.logger = logging.getLogger(__name__)
        self.brand_manager = brand_manager
        self.tool_registry = tool_registry
        self.get_claude_response = claude_response_func

    async def execute(self, decision: str, brand_slug: str):
        """Execute the decision made by Claude for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        if not brand:
            self.logger.error(f"Cannot execute decision: brand {brand_slug} not found")
            return

        # Simple parsing of the decision text to determine the action
        decision_lower = decision.lower()

        if "play a new song" in decision_lower or "select a song" in decision_lower:
            await self._select_and_play_song(decision, brand_slug)
        elif "announcement" in decision_lower or "introduce" in decision_lower:
            await self._make_announcement(decision, brand_slug)
        elif "audience feedback" in decision_lower or "check feedback" in decision_lower:
            await self._check_audience_feedback(brand_slug)
        elif "special request" in decision_lower or "process request" in decision_lower:
            await self._process_special_request(decision, brand_slug)
        elif "upcoming events" in decision_lower or "check events" in decision_lower:
            await self._check_upcoming_events(brand_slug)
        else:
            # Generic handling for other types of decisions
            self.logger.info(f"Brand {brand_slug} - Executing general decision: {decision}")

    async def _select_and_play_song(self, decision: str, brand_slug: str):
        """Select and play a song based on the decision for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        queue_mgr = self.tool_registry.get_tool("song_queue_manager")

        if not queue_mgr:
            self.logger.error(f"Brand {brand_slug} - Song queue manager tool not available")
            return

        # Extract genre from decision if mentioned
        genre = None
        if "genre" in decision.lower():
            genre_start = decision.lower().find("genre") + 5
            genre_end = decision.find(".", genre_start)
            if genre_end == -1:
                genre_end = len(decision)
            genre = decision[genre_start:genre_end].strip()

        # Get available songs, filtered by brand profile constraints
        available_songs = queue_mgr.get_available_songs(
            genre=genre,
            limit=20,
            brand_id=brand_slug
        )

        if available_songs:
            # Select first available song for simplicity
            selected_song = available_songs[0]

            # Convert to dictionary if it's a Song object
            song_dict = selected_song
            if hasattr(selected_song, '__dict__'):
                # For Song objects with __dict__ attribute
                song_dict = selected_song.__dict__
            elif not isinstance(selected_song, dict):
                # For Song objects without __dict__ (like dataclasses)
                song_dict = {
                    "id": getattr(selected_song, "id", ""),
                    "title": getattr(selected_song, "title", "Unknown Title"),
                    "artist": getattr(selected_song, "artist", "Unknown Artist"),
                    "genre": getattr(selected_song, "genre", ""),
                    "album": getattr(selected_song, "album", "")
                }

            queue_mgr.add_song(song_dict, brand_id=brand_slug)

            title = getattr(selected_song, 'title', song_dict.get('title', 'Unknown Title'))
            artist = getattr(selected_song, 'artist', song_dict.get('artist', 'Unknown Artist'))

            self.logger.info(f"Brand {brand_slug} - Added song to queue: {title} by {artist}")

            # Generate introduction for the song
            speech_tool = self.tool_registry.get_tool("speech_generator")
            if speech_tool:
                intro_text = f"Next up, we have {title} by {artist}."
                speech_tool.generate_speech(intro_text, brand_id=brand_slug)

            # Update brand context with current song
            if brand:
                brand.update_state("current_song", song_dict)
        else:
            self.logger.warning(f"Brand {brand_slug} - No songs available matching criteria")

    async def _make_announcement(self, decision: str, brand_slug: str):
        """Make an announcement based on the decision for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        speech_tool = self.tool_registry.get_tool("speech_generator")
        if not speech_tool:
            self.logger.error(f"Brand {brand_slug} - Speech generator tool not available")
            return

        # Check announcement frequency based on profile
        if brand and brand.profile:
            freq = brand.profile.announcementFrequency
            if freq == "VERY_LOW":
                # Only make critical announcements
                if not any(kw in decision.lower() for kw in ["urgent", "emergency", "critical", "important"]):
                    self.logger.info(
                        f"Brand {brand_slug} - Skipping non-critical announcement due to VERY_LOW frequency")
                    return

        # Extract announcement text from decision
        announcement_text = decision
        if "announce that" in decision.lower():
            start_idx = decision.lower().find("announce that") + 13
            announcement_text = decision[start_idx:].strip()

        speech_tool.generate_speech(announcement_text, brand_id=brand_slug)
        self.logger.info(f"Brand {brand_slug} - Made announcement: {announcement_text}")

    async def _check_audience_feedback(self, brand_slug: str):
        """Check for audience feedback for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        engagement_tool = self.tool_registry.get_tool("audience_engagement")
        if not engagement_tool:
            self.logger.error(f"Brand {brand_slug} - Audience engagement tool not available")
            return

        feedback = engagement_tool.get_recent_feedback(brand_id=brand_slug)
        if feedback:
            self.logger.info(f"Brand {brand_slug} - Received audience feedback: {feedback}")

            # Update brand context with feedback
            if brand:
                brand.update_state("feedback", feedback)

            # Ask Claude how to respond to the feedback
            prompt = f"Audience feedback received: {feedback}. How should I respond to this feedback?"
            response_decision = await self.get_claude_response(prompt, brand_slug)

            # Execute the response decision
            await self.execute(response_decision, brand_slug)

    async def _process_special_request(self, decision: str, brand_slug: str):
        """Process a special request for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        self.logger.info(f"Brand {brand_slug} - Processing special request: {decision}")

        if "song request" in decision.lower():
            song_recog = self.tool_registry.get_tool("song_recognition")
            queue_mgr = self.tool_registry.get_tool("song_queue_manager")

            if song_recog and queue_mgr:
                request_details = decision[decision.lower().find("song request") + 12:].strip()
                song_info = song_recog.identify_song(request_details, brand_id=brand_slug)

                # Check if the song matches profile constraints
                if song_info and brand and brand.profile:
                    # Check genre constraints
                    song_genre = (song_info.genre if hasattr(song_info, 'genre')
                                  else song_info.get("genre") if isinstance(song_info, dict) else None)

                    if brand.profile.allowedGenres and song_genre and song_genre not in brand.profile.allowedGenres:
                        self.logger.info(f"Brand {brand_slug} - Requested song genre not allowed by profile")
                        return

                    # Check explicit content constraints
                    explicit = (song_info.explicit if hasattr(song_info, 'explicit')
                                else song_info.get("explicit", False) if isinstance(song_info, dict) else False)

                    if not brand.profile.explicitContent and explicit:
                        self.logger.info(
                            f"Brand {brand_slug} - Requested song has explicit content not allowed by profile")
                        return

                if song_info:
                    queue_mgr.add_song(song_info, brand_id=brand_slug)

                    title = (song_info.title if hasattr(song_info, 'title')
                             else song_info.get("title", "Unknown") if isinstance(song_info, dict) else "Unknown")

                    self.logger.info(f"Brand {brand_slug} - Added requested song: {title}")

    async def _check_upcoming_events(self, brand_slug: str):
        """Check for upcoming events for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        calendar_tool = self.tool_registry.get_tool("event_calendar")
        if not calendar_tool:
            self.logger.error(f"Brand {brand_slug} - Event calendar tool not available")
            return

        upcoming_events = calendar_tool.get_upcoming_events(brand_id=brand_slug, time_window_minutes=30)
        if upcoming_events:
            self.logger.info(f"Brand {brand_slug} - Upcoming events: {upcoming_events}")

            # Update brand context with events
            if brand:
                brand.update_state("upcoming_events", upcoming_events)

            # Ask Claude how to prepare for the upcoming event
            event_str = ", ".join([f"{e['title']} at {e['time']}" for e in upcoming_events])
            prompt = f"Upcoming events: {event_str}. How should I prepare for these events?"
            prep_decision = await self.get_claude_response(prompt, brand_slug)

            # Execute the preparation decision
            await self.execute(prep_decision, brand_slug)