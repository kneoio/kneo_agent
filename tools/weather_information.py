#!/usr/bin/env python3
# tools/weather_information.py - Weather Information tool

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from tools.base_tool import BaseTool


class WeatherInformation(BaseTool):
    """Tool for accessing weather information."""

    def _initialize(self):
        """Initialize the Weather Information tool."""
        self.api_key = self.config.get("api_key", "")
        self.cache_duration_minutes = self.config.get("cache_duration_minutes", 30)
        self.default_location = self.config.get("default_location", "New York, NY")
        self.cache_file = self.config.get("cache_file", "data/weather_cache.json")
        self.weather_cache = {}
        self.last_update = {}

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

        # Load cache if available
        if os.path.exists(self.cache_file):
            self._load_cache()

    @property
    def name(self) -> str:
        """Get the name of the tool."""
        return "weather_information"

    @property
    def description(self) -> str:
        """Get a description of the tool."""
        return "Provides access to weather information and forecasts."

    @property
    def category(self) -> str:
        """Get the category of the tool."""
        return "information"

    def get_capabilities(self) -> List[str]:
        """Get a list of capabilities provided by this tool."""
        return [
            "get_current_weather",
            "get_forecast",
            "get_weather_report",
            "get_weather_alert",
            "is_weather_suitable"
        ]

    def get_current_weather(self, location: str = None) -> Dict[str, Any]:
        """
        Get the current weather for a location.

        Args:
            location: Location to get weather for (defaults to configured default)

        Returns:
            Dictionary containing weather information
        """
        location = location or self.default_location

        # Check cache first
        cache_key = f"current_{location}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            # This would use a real weather API in production
            # For demonstration, return placeholder data
            weather_data = self._get_placeholder_weather(location)

            # Cache the result
            self._add_to_cache(cache_key, weather_data)

            return weather_data
        except Exception as e:
            self.logger.error(f"Failed to get current weather for {location}: {e}")
            return {
                "error": str(e),
                "location": location,
                "timestamp": datetime.now().isoformat()
            }

    def get_forecast(self, location: str = None, days: int = 5) -> Dict[str, Any]:
        """
        Get a weather forecast for a location.

        Args:
            location: Location to get forecast for (defaults to configured default)
            days: Number of days to forecast

        Returns:
            Dictionary containing forecast information
        """
        location = location or self.default_location
        days = min(max(1, days), 10)  # Limit between 1 and 10 days

        # Check cache first
        cache_key = f"forecast_{location}_{days}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            # This would use a real weather API in production
            # For demonstration, return placeholder data
            forecast_data = {
                "location": location,
                "days": days,
                "forecast": [self._get_placeholder_forecast(location, i) for i in range(days)],
                "timestamp": datetime.now().isoformat()
            }

            # Cache the result
            self._add_to_cache(cache_key, forecast_data)

            return forecast_data
        except Exception as e:
            self.logger.error(f"Failed to get forecast for {location}: {e}")
            return {
                "error": str(e),
                "location": location,
                "days": days,
                "timestamp": datetime.now().isoformat()
            }

    def get_weather_report(self, location: str = None) -> str:
        """
        Get a formatted weather report suitable for announcements.

        Args:
            location: Location to get weather for (defaults to configured default)

        Returns:
            Formatted weather report string
        """
        location = location or self.default_location

        try:
            weather = self.get_current_weather(location)
            forecast = self.get_forecast(location, days=1)

            if "error" in weather or "error" in forecast:
                return f"I'm sorry, weather information for {location} is currently unavailable."

            # Format the report
            current = weather
            tomorrow = forecast["forecast"][0]

            report = f"Weather report for {location}. Currently it's {current['condition']} "
            report += f"with a temperature of {current['temperature']}. "

            if "feels_like" in current and current["feels_like"] != current["temperature"]:
                report += f"Feels like {current['feels_like']}. "

            report += f"Humidity is {current['humidity']}% "

            if "wind" in current:
                report += f"and wind is {current['wind']}. "

            report += "For tomorrow, "
            report += f"expect {tomorrow['condition']} with a high of {tomorrow['high']} "
            report += f"and a low of {tomorrow['low']}."

            return report
        except Exception as e:
            self.logger.error(f"Failed to generate weather report for {location}: {e}")
            return f"I'm sorry, weather information for {location} is currently unavailable."

    def get_weather_alert(self, location: str = None) -> Optional[Dict[str, Any]]:
        """
        Get any active weather alerts for a location.

        Args:
            location: Location to get alerts for (defaults to configured default)

        Returns:
            Dictionary containing alert information or None if no alerts
        """
        location = location or self.default_location

        # Check cache first
        cache_key = f"alert_{location}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            # This would use a real weather API in production
            # For demonstration, return placeholder data (usually no alerts)
            if datetime.now().minute % 20 == 0:  # Simulate occasional alerts
                alert_data = {
                    "location": location,
                    "type": "weather_advisory",
                    "severity": "moderate",
                    "headline": "Rain Advisory",
                    "description": "Heavy rain expected in the afternoon. Possibility of local flooding in low-lying areas.",
                    "start_time": (datetime.now() + timedelta(hours=2)).isoformat(),
                    "end_time": (datetime.now() + timedelta(hours=8)).isoformat(),
                    "timestamp": datetime.now().isoformat()
                }

                # Cache the result
                self._add_to_cache(cache_key, alert_data)

                return alert_data
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to get weather alerts for {location}: {e}")
            return None

    def is_weather_suitable(self, activity: str, location: str = None) -> Dict[str, Any]:
        """
        Determine if the weather is suitable for a specific activity.

        Args:
            activity: The activity to check suitability for
            location: Location to check weather (defaults to configured default)

        Returns:
            Dictionary containing suitability assessment
        """
        location = location or self.default_location
        weather = self.get_current_weather(location)

        if "error" in weather:
            return {
                "suitable": None,
                "confidence": 0,
                "reason": "Weather information unavailable",
                "activity": activity,
                "location": location,
                "timestamp": datetime.now().isoformat()
            }

        # Simple rules for different activities
        # In a real implementation, this would be much more sophisticated
        activity = activity.lower()

        if activity in ["walking", "running", "jogging", "hiking"]:
            # Check for extreme weather
            condition = weather.get("condition", "").lower()
            temp = self._extract_temperature(weather.get("temperature", "0"))

            if any(w in condition for w in ["snow", "rain", "storm", "thunder"]):
                suitable = False
                reason = f"Not suitable due to {condition} conditions"
            elif temp < 32:
                suitable = False
                reason = "Temperature too cold"
            elif temp > 95:
                suitable = False
                reason = "Temperature too hot"
            else:
                suitable = True
                reason = "Weather conditions are favorable"

            confidence = 0.8

        elif activity in ["swimming", "beach"]:
            condition = weather.get("condition", "").lower()
            temp = self._extract_temperature(weather.get("temperature", "0"))

            if any(w in condition for w in ["rain", "storm", "thunder"]):
                suitable = False
                reason = f"Not suitable due to {condition} conditions"
            elif temp < 75:
                suitable = False
                reason = "Temperature too cool for swimming"
            else:
                suitable = True
                reason = "Weather conditions are favorable"

            confidence = 0.7

        elif activity in ["skiing", "snowboarding"]:
            condition = weather.get("condition", "").lower()

            if "snow" in condition:
                suitable = True
                reason = "Snowy conditions are perfect"
            elif "rain" in condition:
                suitable = False
                reason = "Rain makes for poor skiing conditions"
            else:
                suitable = None
                reason = "Need more information about snow conditions"
                confidence = 0.5
                return {
                    "suitable": suitable,
                    "confidence": confidence,
                    "reason": reason,
                    "activity": activity,
                    "location": location,
                    "weather": weather,
                    "timestamp": datetime.now().isoformat()
                }

            confidence = 0.8

        else:
            # Generic suitability for unknown activities
            condition = weather.get("condition", "").lower()

            if any(w in condition for w in ["storm", "thunder", "hurricane", "tornado"]):
                suitable = False
                reason = f"Severe weather ({condition}) makes outdoor activities unsafe"
            elif any(w in condition for w in ["rain", "snow"]):
                suitable = False
                reason = f"{condition.capitalize()} may interfere with {activity}"
            else:
                suitable = True
                reason = "Weather conditions appear suitable"

            confidence = 0.6

        return {
            "suitable": suitable,
            "confidence": confidence,
            "reason": reason,
            "activity": activity,
            "location": location,
            "weather": weather,
            "timestamp": datetime.now().isoformat()
        }

    def _extract_temperature(self, temp_str: str) -> float:
        """
        Extract a numeric temperature from a string like "75°F" or "24°C".

        Args:
            temp_str: Temperature string

        Returns:
            Temperature value in degrees
        """
        try:
            # Remove non-numeric characters except decimal point
            temp = ''.join(c for c in temp_str if c.isdigit() or c == '.')
            return float(temp)
        except (ValueError, TypeError):
            return 0

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if available and not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not available/expired
        """
        if key not in self.weather_cache or key not in self.last_update:
            return None

        # Check if cache has expired
        last_update_time = datetime.fromisoformat(self.last_update[key])
        cache_expiry = last_update_time + timedelta(minutes=self.cache_duration_minutes)

        if datetime.now() > cache_expiry:
            return None

        return self.weather_cache[key]

    def _add_to_cache(self, key: str, data: Dict[str, Any]):
        """
        Add data to cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        self.weather_cache[key] = data
        self.last_update[key] = datetime.now().isoformat()

        # Save cache to file
        self._save_cache()

    def _save_cache(self):
        """Save the cache to a file."""
        try:
            cache_data = {
                "weather_cache": self.weather_cache,
                "last_update": self.last_update,
                "saved_at": datetime.now().isoformat()
            }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save weather cache: {e}")

    def _load_cache(self):
        """Load the cache from a file."""
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            self.weather_cache = cache_data.get("weather_cache", {})
            self.last_update = cache_data.get("last_update", {})

            self.logger.info(f"Loaded weather cache with {len(self.weather_cache)} entries")
        except Exception as e:
            self.logger.error(f"Failed to load weather cache: {e}")

    def _get_placeholder_weather(self, location: str) -> Dict[str, Any]:
        """
        Generate placeholder weather data for testing.

        Args:
            location: Location string

        Returns:
            Dictionary with placeholder weather data
        """
        # Use the hash of the location and current hour to generate consistent data
        location_hash = hash(location)
        hour_hash = hash(datetime.now().strftime("%Y-%m-%d-%H"))
        combined_hash = (location_hash + hour_hash) % 1000

        # Generate conditions based on hash
        conditions = ["Clear", "Partly Cloudy", "Cloudy", "Overcast", "Light Rain", "Rain", "Heavy Rain",
                      "Thunderstorm", "Snow", "Foggy"]
        condition_index = combined_hash % len(conditions)
        condition = conditions[condition_index]

        # Generate temperature (30-95°F)
        temp_base = 30 + (combined_hash % 65)
        temp_variation = (datetime.now().hour - 6) % 24  # Peak at noon-2pm
        if temp_variation > 12:
            temp_variation = 24 - temp_variation
        temperature = temp_base + temp_variation

        # Generate feels like
        feels_like = temperature + (combined_hash % 7) - 3

        # Generate humidity (30-90%)
        humidity = 30 + (combined_hash % 60)

        # Generate wind
        wind_speed = 5 + (combined_hash % 20)
        wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        wind_dir = wind_directions[combined_hash % len(wind_directions)]
        wind = f"{wind_speed} mph {wind_dir}"

        return {
            "location": location,
            "condition": condition,
            "temperature": f"{temperature}°F",
            "feels_like": f"{feels_like}°F",
            "humidity": humidity,
            "wind": wind,
            "timestamp": datetime.now().isoformat()
        }

    def _get_placeholder_forecast(self, location: str, days_ahead: int) -> Dict[str, Any]:
        """
        Generate placeholder forecast data for testing.

        Args:
            location: Location string
            days_ahead: Number of days in the future

        Returns:
            Dictionary with placeholder forecast data
        """
        # Use location and day to generate consistent data
        forecast_date = datetime.now() + timedelta(days=days_ahead)
        location_hash = hash(location)
        date_hash = hash(forecast_date.strftime("%Y-%m-%d"))
        combined_hash = (location_hash + date_hash) % 1000

        # Generate conditions based on hash
        conditions = ["Clear", "Partly Cloudy", "Cloudy", "Overcast", "Light Rain", "Rain", "Heavy Rain",
                      "Thunderstorm", "Snow", "Foggy"]
        condition_index = combined_hash % len(conditions)
        condition = conditions[condition_index]

        # Generate temperature range (higher variation for further days)
        temp_base = 30 + (combined_hash % 65)
        high = temp_base + (5 + (combined_hash % 10))
        low = temp_base - (8 + (combined_hash % 15))

        # Generate precipitation chance
        precip_chance = (
                combined_hash % 100) if "Rain" in condition or "Snow" in condition or "Thunder" in condition else (
                combined_hash % 30)

        return {
            "date": forecast_date.strftime("%Y-%m-%d"),
            "day_of_week": forecast_date.strftime("%A"),
            "condition": condition,
            "high": f"{high}°F",
            "low": f"{low}°F",
            "precipitation_chance": f"{precip_chance}%"
        }
