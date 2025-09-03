#!/usr/bin/env python3
import json
import requests

def get_weather(city="Leiria"):
    try:
        # Geocoding
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
        geo_r = requests.get(geo_url, params=geo_params)
        geo_data = geo_r.json()

        if not geo_data.get("results"):
            return f"City {city} not found"

        result = geo_data["results"][0]
        lat, lon = result["latitude"], result["longitude"]

        # Weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto"
        }
        weather_r = requests.get(weather_url, params=weather_params)
        weather_data = weather_r.json()

        current = weather_data["current"]
        weather_codes = {0: "Clear", 1: "Clear", 2: "Cloudy", 3: "Overcast", 61: "Rain", 95: "Storm"}
        condition = weather_codes.get(current["weather_code"], f"Code {current['weather_code']}")

        return f"{city}: {current['temperature_2m']}�C, {condition}, {current['relative_humidity_2m']}% humidity, {current['wind_speed_10m']} km/h wind"
    except Exception as e:
        return f"Weather error: {str(e)}"

while True:
    try:
        line = input()
        req = json.loads(line)
        method = req.get("method", "")
        req_id = req.get("id", 1)

        if method == "initialize":
            response = {"jsonrpc":"2.0","id":req_id,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}}}}
        elif method == "tools/list":
            response = {"jsonrpc":"2.0","id":req_id,"result":{"tools":[{"name":"get_weather","description":"Get weather for any city","inputSchema":{"type":"object","properties":{"city":{"type":"string","description":"City name"}},"required":["city"]}}]}}
        elif method == "tools/call":
            tool_name = req.get("params", {}).get("name", "")
            if tool_name == "get_weather":
                city = req.get("params", {}).get("arguments", {}).get("city", "Leiria")
                weather = get_weather(city)
                response = {"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":weather}]}}
            else:
                response = {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Unknown tool"}}
        else:
            response = {"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":"Unknown method"}}

        print(json.dumps(response), flush=True)

    except EOFError:
        break
