#!/usr/bin/env python3
from datetime import datetime
from typing import Optional
from models.brand import Brand


class PromptBuilder:
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    def build_system_prompt(self, brand: Optional[Brand]) -> str:
        """Build a system prompt for Claude based on current context and environment."""
        if not brand:
            return "You are an AI DJ Agent. Please help manage music and announcements."

        # Focus on using slugName instead of ID for brand identity
        brand_name = brand.slugName
        country = brand.country

        # Get profile information
        profile = brand.profile
        profile_name = profile.name if profile else "generic"
        language = profile.language if profile and profile.language else "en"

        # Get state information
        state = brand.get_state()

        prompt = f"""You are an AI DJ Agent for {brand_name} radio station in {country} with a {profile_name} environment focus.
Please respond in {language} language.

Your radio station identity:
- Station Name: {brand_name}
- Country: {country} 
- Environment Type: {profile_name}
- Environment Description: {profile.description if profile else "None"}

Current context:
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Current Song: {state.get('current_song', 'None')}
- Audience: {state.get('audience_info', {})}
- Current/Upcoming Events: {state.get('upcoming_events', [])}
- Last Action: {state.get('last_action', 'None')}
- Recent Feedback: {state.get('feedback', [])}

Environment profile guidelines:
- Allowed Genres: {', '.join(profile.allowedGenres) if profile and profile.allowedGenres else "All genres"}
- Announcement Frequency: {profile.announcementFrequency if profile else "MEDIUM"}
- Explicit Content Allowed: {"Yes" if profile and profile.explicitContent else "No"}

Your available tools:
{self.tool_registry.get_tool_descriptions()}

When deciding what to do next, consider:
1. Your specific radio station identity and environment
2. Appropriate music selection from allowed genres
3. Engaging commentary that's suitable for your audience
4. Timing of announcements and transitions based on announcement frequency
5. Response to audience feedback and requests

Maintain an engaging, appropriate tone for {brand_name} in a {profile_name} setting.
"""
        return prompt