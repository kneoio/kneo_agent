#!/usr/bin/env python3
# tools/time_announcer.py - Time Announcer tool

import random
from datetime import datetime, timedelta
from typing import List

from tools.base_tool import BaseTool


class TimeAnnouncer(BaseTool):
    """Tool for generating time announcements."""

    def _initialize(self):
        """Initialize the Time Announcer."""
        self.announcement_frequency = self.config.get("announcement_frequency", "hourly")
        self.time_formats = self.config.get("time_formats", [
            "It's {hour12} o'clock {ampm}",
            "The time is now {hour12}:{minute:02d} {ampm}",
            "Time check: {hour12}:{minute:02d} {ampm}"
        ])
        self.randomization_factor = self.config.get("randomization_factor", 0.3)
        self.last_announcement = None
        self.next_announcement = self._calculate_next_announcement()

    @property
    def name(self) -> str:
        return "time_announcer"

    @property
    def description(self) -> str:
        return "Generates time announcements at appropriate intervals."

    @property
    def category(self) -> str:
        return "presentation"

    def get_capabilities(self) -> List[str]:
        return [
            "announce_time",
            "get_next_announcement_time",
            "is_announcement_due",
            "get_time_until_event",
            "format_duration"
        ]

    def announce_time(self, format_template: str = None) -> str:
        """Generate a time announcement string."""
        now = datetime.now()

        # Update last announcement time and calculate next one
        self.last_announcement = now
        self.next_announcement = self._calculate_next_announcement()

        # Use provided format or select a random one
        if not format_template:
            format_template = random.choice(self.time_formats)

        # Format the time
        hour12 = now.hour if now.hour <= 12 else now.hour - 12
        if hour12 == 0:
            hour12 = 12

        ampm = "AM" if now.hour < 12 else "PM"

        try:
            announcement = format_template.format(
                hour=now.hour,
                hour12=hour12,
                minute=now.minute,
                second=now.second,
                ampm=ampm,
                day=now.day,
                month=now.month,
                year=now.year
            )
        except Exception as e:
            self.logger.error(f"Error formatting time announcement: {e}")
            announcement = f"It's {hour12}:{now.minute:02d} {ampm}"

        return announcement

    def get_next_announcement_time(self) -> datetime:
        """Get the time of the next scheduled announcement."""
        return self.next_announcement

    def is_announcement_due(self) -> bool:
        """Check if it's time for a new announcement."""
        now = datetime.now()
        return now >= self.next_announcement

    def get_time_until_event(self, event_time: datetime) -> str:
        """Generate a formatted string for the time until an event."""
        now = datetime.now()

        if event_time < now:
            return "This event has already passed"

        # Calculate time difference
        time_diff = event_time - now
        total_seconds = int(time_diff.total_seconds())

        days = total_seconds // (24 * 60 * 60)
        hours = (total_seconds % (24 * 60 * 60)) // (60 * 60)
        minutes = (total_seconds % (60 * 60)) // 60

        # Format the time difference
        if days > 0:
            if hours > 0:
                return f"{days} day{'s' if days > 1 else ''} and {hours} hour{'s' if hours > 1 else ''} from now"
            else:
                return f"{days} day{'s' if days > 1 else ''} from now"
        elif hours > 0:
            if minutes > 0:
                return f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes > 1 else ''} from now"
            else:
                return f"{hours} hour{'s' if hours > 1 else ''} from now"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''} from now"
        else:
            return "less than a minute from now"

    def format_duration(self, seconds: int) -> str:
        """Format a duration in seconds to a human-readable string."""
        if seconds < 0:
            return "invalid duration"

        days = seconds // (24 * 60 * 60)
        hours = (seconds % (24 * 60 * 60)) // (60 * 60)
        minutes = (seconds % (60 * 60)) // 60
        remaining_seconds = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if remaining_seconds > 0 and len(parts) < 2:
            parts.append(f"{remaining_seconds} second{'s' if remaining_seconds > 1 else ''}")

        if not parts:
            return "0 seconds"

        if len(parts) == 1:
            return parts[0]

        return f"{', '.join(parts[:-1])} and {parts[-1]}"

    def _calculate_next_announcement(self) -> datetime:
        """Calculate when the next time announcement should occur."""
        now = datetime.now()

        # Base calculation on announcement frequency
        if self.announcement_frequency == "hourly":
            # Next hour
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif self.announcement_frequency == "half_hourly":
            # Next :00 or :30
            if now.minute < 30:
                next_time = now.replace(minute=30, second=0, microsecond=0)
            else:
                next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif self.announcement_frequency == "quarter_hourly":
            # Next :00, :15, :30, or :45
            minute = now.minute
            if minute < 15:
                next_time = now.replace(minute=15, second=0, microsecond=0)
            elif minute < 30:
                next_time = now.replace(minute=30, second=0, microsecond=0)
            elif minute < 45:
                next_time = now.replace(minute=45, second=0, microsecond=0)
            else:
                next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif self.announcement_frequency == "random":
            # Random time within the next 30-90 minutes
            minutes_to_add = random.randint(30, 90)
            next_time = now + timedelta(minutes=minutes_to_add)
        else:
            # Default to hourly
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        # Add randomization if configured
        if self.randomization_factor > 0:
            # Calculate maximum deviation in minutes
            max_deviation_minutes = 0

            if self.announcement_frequency == "hourly":
                max_deviation_minutes = int(60 * self.randomization_factor)
            elif self.announcement_frequency == "half_hourly":
                max_deviation_minutes = int(30 * self.randomization_factor)
            elif self.announcement_frequency == "quarter_hourly":
                max_deviation_minutes = int(15 * self.randomization_factor)

            # Apply random deviation
            if max_deviation_minutes > 0:
                deviation_minutes = random.randint(-max_deviation_minutes, max_deviation_minutes)
                next_time += timedelta(minutes=deviation_minutes)

        return next_time
