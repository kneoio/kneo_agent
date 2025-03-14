#!/usr/bin/env python3
# core/state.py - System state management

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class SystemState:
    """Manages the state of the AI DJ Agent system."""

    def __init__(self):
        self.profiles = {
            "generic": {
                "description": "Generic environment suitable for most settings.",
                "language": "en",
                "allowed_genres": ["pop", "rock", "jazz", "classical", "electronic"],
                "volume_level": "medium",
                "announcement_frequency": "medium",
                "explicit_content": False,
                "custom": False
            }
        }
        self.logger = logging.getLogger(__name__)
        self.state = {
            "current_song": None,
            "queue": [],
            "last_action": None,
            "last_action_time": None,
            "audience_info": {
                "estimated_count": 0,
                "demographics": {},
                "feedback": []
            },
            "environment_profile": "generic",
            "current_events": [],
            "upcoming_events": [],
            "weather": None,
            "announcements": [],
            "special_requests": []
        }

        # Environment profiles with their guidelines
        self.environment_profiles = {
            "generic": "Standard profile with balanced music and announcements.",
            "care_center": "Focus on nostalgia, gentle volume, cognitive stimulation.",
            "hospital": "Calming selections, limited announcement volume, wellness themes.",
            "school": "Age-appropriate content, educational ties, energy management.",
            "car_workshop": "Upbeat tempo, industry-appropriate language, ambient volume.",
            "mall": "Family-friendly content, shopping-compatible tempo, promotional integration.",
            "office": "Work-appropriate selections, productivity focus, time-aware programming.",
            "family_event": "Occasion-specific content, all-ages appropriate, celebration themes.",
            "student_dorms": "Contemporary selections, social connection themes, study-time awareness."
        }

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get the current state of the system.

        Returns:
            Dict containing the current system state
        """
        # Update the timestamp
        self.state["timestamp"] = datetime.now().isoformat()
        return self.state

    def update_current_song(self, song: Dict[str, Any]):
        """
        Update the currently playing song.

        Args:
            song: Dictionary containing song information
        """
        self.state["current_song"] = song
        self.logger.debug(f"Updated current song: {song.get('title', 'Unknown')}")

    def update_queue(self, queue: List[Dict[str, Any]]):
        """
        Update the song queue.

        Args:
            queue: List of songs in the queue
        """
        self.state["queue"] = queue
        self.logger.debug(f"Updated queue with {len(queue)} songs")

    def update_audience_info(self, audience_info: Dict[str, Any]):
        """
        Update information about the audience.

        Args:
            audience_info: Dictionary containing audience information
        """
        self.state["audience_info"] = audience_info
        self.logger.debug("Updated audience information")

    def update_audience_feedback(self, feedback: Dict[str, Any]):
        """
        Add new audience feedback.

        Args:
            feedback: Dictionary containing feedback information
        """
        feedback["timestamp"] = datetime.now().isoformat()
        self.state["audience_info"]["feedback"].append(feedback)

        # Limit feedback history to last 20 items
        if len(self.state["audience_info"]["feedback"]) > 20:
            self.state["audience_info"]["feedback"] = self.state["audience_info"]["feedback"][-20:]

        self.logger.debug(f"Added audience feedback: {feedback.get('message', 'No message')}")

    def update_environment_profile(self, profile: str):
        """
        Update the current environment profile.

        Args:
            profile: Name of the environment profile
        """
        if profile not in self.environment_profiles:
            self.logger.warning(f"Unknown environment profile: {profile}, using generic")
            profile = "generic"

        self.state["environment_profile"] = profile
        self.logger.info(f"Updated environment profile to: {profile}")

    def get_environment_profile(self, profile_name: str) -> str:
        """
        Get details of a specific environment profile.

        Args:
            profile_name: Name of the environment profile

        Returns:
            String containing profile guidelines
        """
        return self.environment_profiles.get(profile_name, self.environment_profiles["generic"])

    def update_current_events(self, events: List[Dict[str, Any]]):
        """
        Update the list of current events.

        Args:
            events: List of current events
        """
        self.state["current_events"] = events
        self.logger.debug(f"Updated current events: {len(events)} events")

    def update_upcoming_events(self, events: List[Dict[str, Any]]):
        """
        Update the list of upcoming events.

        Args:
            events: List of upcoming events
        """
        self.state["upcoming_events"] = events
        self.logger.debug(f"Updated upcoming events: {len(events)} events")

    def get_current_events(self) -> List[Dict[str, Any]]:
        """
        Get the list of current events.

        Returns:
            List of current events
        """
        return self.state["current_events"]

    def get_audience_info(self) -> Dict[str, Any]:
        """
        Get information about the audience.

        Returns:
            Dictionary containing audience information
        """
        return self.state["audience_info"]

    def update_weather(self, weather: Dict[str, Any]):
        """
        Update weather information.

        Args:
            weather: Dictionary containing weather information
        """
        self.state["weather"] = weather
        self.logger.debug(f"Updated weather information: {weather.get('condition', 'Unknown')}")

    def add_announcement(self, announcement: Dict[str, Any]):
        """
        Add a new announcement to the history.

        Args:
            announcement: Dictionary containing announcement information
        """
        announcement["timestamp"] = datetime.now().isoformat()
        self.state["announcements"].append(announcement)

        # Limit announcement history to last 20 items
        if len(self.state["announcements"]) > 20:
            self.state["announcements"] = self.state["announcements"][-20:]

        self.logger.debug(f"Added announcement: {announcement.get('text', 'No text')}")

    def add_special_request(self, request: Dict[str, Any]):
        """
        Add a new special request.

        Args:
            request: Dictionary containing request information
        """
        request["timestamp"] = datetime.now().isoformat()
        self.state["special_requests"].append(request)

        # Limit request history to last 20 items
        if len(self.state["special_requests"]) > 20:
            self.state["special_requests"] = self.state["special_requests"][-20:]

        self.logger.debug(f"Added special request: {request.get('text', 'No text')}")

    def update_last_action(self, action: str):
        """
        Update the last action performed by the system.

        Args:
            action: Description of the action
        """
        self.state["last_action"] = action
        self.state["last_action_time"] = datetime.now().isoformat()
        self.logger.debug(f"Updated last action: {action[:50]}...")

    def get_profile_object(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """Get the profile object itself rather than the text description."""
        return self.profiles.get(profile_name, self.profiles.get("generic", {}))
    
    def save_state(self, filepath: str) -> bool:
        """
        Save the current state to a file.

        Args:
            filepath: Path to save the state file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.state, f, indent=2)
            self.logger.info(f"Saved state to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save state to {filepath}: {e}")
            return False

    def load_state(self, filepath: str) -> bool:
        """
        Load state from a file.

        Args:
            filepath: Path to the state file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                loaded_state = json.load(f)
            self.state.update(loaded_state)
            self.logger.info(f"Loaded state from {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load state from {filepath}: {e}")
            return False