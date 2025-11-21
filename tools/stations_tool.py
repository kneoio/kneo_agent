import logging
from typing import Dict, Any, Optional, List

from api.stations_api import StationsAPI

logger = logging.getLogger(__name__)

_stations_api: Optional[StationsAPI] = None


def set_stations_api(api: StationsAPI) -> None:
    global _stations_api
    _stations_api = api


async def list_stations(statuses: Optional[List[str]] = None,
                        country: Optional[str] = None,
                        dj_language: Optional[str] = None,
                        query: Optional[str] = None) -> Dict[str, Any]:
    if not _stations_api:
        logger.error("StationsAPI not initialized")
        return {"error": "StationsAPI not available"}
    api = _stations_api
    result = api.get_stations(statuses=statuses, country=country, dj_language=dj_language, query=query)
    if result is None:
        return {"error": "stations_api_unavailable"}
    return result


async def get_station_live(slug: str) -> Dict[str, Any]:
    if not _stations_api:
        logger.error("StationsAPI not initialized")
        return {"error": "StationsAPI not available"}
    api = _stations_api
    if not slug:
        return {"error": "slug is required"}
    result = api.get_station_live(slug)
    if result is None:
        return {"error": "station_live_unavailable", "slugName": slug}
    return result


def get_list_stations_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "list_stations",
            "description": "List available radio stations with optional filters: statuses, country, DJ language, search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "statuses": {"type": "array", "items": {"type": "string"}},
                    "country": {"type": "string"},
                    "dj_language": {"type": "string"},
                    "query": {"type": "string"}
                },
                "required": []
            }
        }
    }


def get_station_live_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "get_station_live",
            "description": "Get live status for a radio station by slug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string"}
                },
                "required": ["slug"]
            }
        }
    }
