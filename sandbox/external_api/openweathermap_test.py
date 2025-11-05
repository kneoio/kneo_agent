import requests
from core.config import load_config

# Load API key from config
cfg = load_config("../../config.yaml")
api_key = cfg.get("api_services").get("openweathermap").get("api_key")

# One Call API 3.0 endpoint
BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"

# Example coordinates (London)
lat = 51.5074
lon = -0.1278

# API parameters
params = {
    "lat": lat,
    "lon": lon,
    "appid": api_key,
    "units": "metric",  # Use 'imperial' for Fahrenheit, 'metric' for Celsius
    "exclude": ""  # Can exclude: current,minutely,hourly,daily,alerts
}

try:
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()
    
    # Print current weather
    if "current" in data:
        current = data["current"]
        print("=== CURRENT WEATHER ===")
        print(f"Temperature: {current.get('temp')}°C")
        print(f"Feels like: {current.get('feels_like')}°C")
        print(f"Humidity: {current.get('humidity')}%")
        print(f"Weather: {current.get('weather', [{}])[0].get('description', 'N/A')}")
        print(f"Wind speed: {current.get('wind_speed')} m/s")
        print()
    
    # Print daily forecast (first 3 days)
    if "daily" in data:
        print("=== DAILY FORECAST ===")
        for i, day in enumerate(data["daily"][:3]):
            print(f"Day {i+1}:")
            print(f"  Temp (day): {day.get('temp', {}).get('day')}°C")
            print(f"  Temp (min/max): {day.get('temp', {}).get('min')}°C / {day.get('temp', {}).get('max')}°C")
            print(f"  Weather: {day.get('weather', [{}])[0].get('description', 'N/A')}")
            print(f"  Precipitation probability: {day.get('pop', 0) * 100}%")
            print()
    
    # Print hourly forecast (first 3 hours)
    if "hourly" in data:
        print("=== HOURLY FORECAST (Next 3 hours) ===")
        for i, hour in enumerate(data["hourly"][:3]):
            print(f"Hour {i+1}:")
            print(f"  Temp: {hour.get('temp')}°C")
            print(f"  Weather: {hour.get('weather', [{}])[0].get('description', 'N/A')}")
            print(f"  Precipitation probability: {hour.get('pop', 0) * 100}%")
            print()
    
    # Print alerts if any
    if "alerts" in data and data["alerts"]:
        print("=== WEATHER ALERTS ===")
        for alert in data["alerts"]:
            print(f"Event: {alert.get('event')}")
            print(f"Description: {alert.get('description')}")
            print()

except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
