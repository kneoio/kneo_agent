#!/usr/bin/env python3
import requests
from typing import Dict, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    """Input for weather tool"""
    city: str = Field(description="City name to get weather for")


class WeatherTool(BaseTool):
    """Weather tool for LangGraph agents"""
    name = "get_weather"
    description = "Get current weather information for any city"
    args_schema = WeatherInput

    def _run(self, city: str) -> str:
        """Get weather for a city"""
        try:
            # Geocoding API
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {"name": city, "count": 1, "format": "json"}

            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            geo_data = geo_response.json()

            if not geo_data.get("results"):
                return f"City '{city}' not found"

            result = geo_data["results"][0]
            lat, lon = result["latitude"], result["longitude"]

            # Weather API
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m,pressure_msl",
                "timezone": "auto"
            }

            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            weather_data = weather_response.json()

            current = weather_data["current"]

            # Weather condition mapping
            weather_codes = {
                0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
                95: "Thunderstorm"
            }

            condition = weather_codes.get(current.get('weather_code', 0), "Unknown")

            return f"""Weather in {city}:
Temperature: {current['temperature_2m']}°C
Condition: {condition}
Humidity: {current['relative_humidity_2m']}%
Wind: {current['wind_speed_10m']} km/h
Pressure: {current['pressure_msl']} hPa
Updated: {current['time']}"""

        except Exception as e:
            return f"Error getting weather for {city}: {str(e)}"


# For LangGraph usage
def create_weather_tool():
    """Create weather tool for LangGraph"""
    return WeatherTool()


# Alternative simple function approach
def get_weather_simple(city: str) -> str:
    """Simple weather function for LangGraph nodes"""
    try:
        # Geocoding
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_response = requests.get(geo_url, params={"name": city, "count": 1, "format": "json"})
        geo_data = geo_response.json()

        if not geo_data.get("results"):
            return f"City '{city}' not found"

        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]

        # Weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto"
        }

        weather_response = requests.get(weather_url, params=weather_params)
        current = weather_response.json()["current"]

        return f"{city}: {current['temperature_2m']}°C, {current['relative_humidity_2m']}% humidity, {current['wind_speed_10m']} km/h wind"

    except Exception as e:
        return f"Weather error: {str(e)}"


# Example LangGraph integration
def weather_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node that gets weather"""
    city = state.get("city", "Leiria")
    weather = get_weather_simple(city)

    return {
        **state,
        "weather": weather,
        "messages": state.get("messages", []) + [f"Weather: {weather}"]
    }


if __name__ == "__main__":
    # Test the tool
    tool = create_weather_tool()
    result = tool.run("Leiria")
    print(result)

    print("\n" + "=" * 40)

    # Test the simple function
    simple_result = get_weather_simple("Lisbon")
    print(simple_result)