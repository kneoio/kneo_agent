#!/usr/bin/env python3
from typing import Dict, Any, List, Optional

from api.environment_profile_api import EnvironmentProfileAPI
from tools.base_tool import BaseTool


def get_capabilities() -> List[str]:
    return [
        "get_profile",
        "set_current_profile",
        "get_current_profile",
        "list_profiles",
        "get_profile_guidelines",
        "get_allowed_genres"
    ]


class EnvironmentProfileManager(BaseTool):
    def _initialize(self):
        self.api = EnvironmentProfileAPI(self.config)
        self.profiles = {}
        self.current_profile = "generic"
        self.brand_id = self.config.get("brand_id")

    @property
    def name(self) -> str:
        return "environment_profiles"

    @property
    def description(self) -> str:
        return "Manages environment profiles for different settings."

    @property
    def category(self) -> str:
        return "configuration"

    def get_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        if profile_name in self.profiles:
            return self.profiles[profile_name]

        # Try loading directly from API if not in cache
        profile = self.api.get_profile(profile_name)
        if profile:
            self.profiles[profile_name] = profile
            return profile
        return None

    def set_current_profile(self, profile_name: str) -> bool:
        profile = self.get_profile(profile_name)
        if not profile:
            self.logger.error(f"Cannot set current profile: profile '{profile_name}' not found")
            return False

        self.current_profile = profile_name
        self.logger.info(f"Set current environment profile to: {profile_name}")
        return True

    def get_current_profile(self) -> Dict[str, Any]:
        return self.get_profile(self.current_profile) or self.get_profile("generic") or {}

    def list_profiles(self) -> List[Dict[str, Any]]:
        result = []
        for name, profile in self.profiles.items():
            summary = {
                "name": name,
                "description": profile.get("description", ""),
                "custom": profile.get("custom", False),
                "current": (name == self.current_profile)
            }
            result.append(summary)
        return result

    def get_profile_guidelines(self, profile_name: str = None) -> str:
        profile_name = profile_name or self.current_profile
        profile = self.get_profile(profile_name) or self.get_profile("generic") or {}

        description = profile.get("description", "No description available.")
        allowed_genres = profile.get("allowed_genres", [])
        volume_level = profile.get("volume_level", "medium")
        announcement_frequency = profile.get("announcement_frequency", "medium")
        explicit_content = "allowed" if profile.get("explicit_content", False) else "not allowed"

        guidelines = f"Environment Profile: {profile_name}\n\n"
        guidelines += f"{description}\n\n"
        guidelines += f"Volume Level: {volume_level}\n"
        guidelines += f"Announcement Frequency: {announcement_frequency}\n"
        guidelines += f"Explicit Content: {explicit_content}\n"

        if allowed_genres:
            guidelines += f"Recommended Genres: {', '.join(allowed_genres)}\n"

        if "special_instructions" in profile:
            guidelines += f"\nSpecial Instructions:\n{profile['special_instructions']}\n"

        return guidelines

    def get_allowed_genres(self, profile_name: str = None) -> List[str]:
        profile_name = profile_name or self.current_profile
        profile = self.get_profile(profile_name) or self.get_profile("generic") or {}
        return profile.get("allowed_genres", [])
