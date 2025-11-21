import logging
from typing import Optional, List, Dict, Any

from api.broadcaster_client import BroadcasterAPIClient


class StationsAPI:
    def __init__(self, config):
        self.client = BroadcasterAPIClient(config)
        self.logger = logging.getLogger(__name__)

    def _build_query(self, statuses: Optional[List[str]], country: Optional[str], dj_language: Optional[str], query: Optional[str]) -> str:
        params = []
        if statuses:
            joined = ",".join([s for s in statuses if isinstance(s, str) and s.strip()])
            if joined:
                params.append(f"statuses={joined}")
        if country and country.strip():
            params.append(f"country={country.strip()}")
        if dj_language and dj_language.strip():
            params.append(f"djLanguage={dj_language.strip()}")
        if query and query.strip():
            params.append(f"q={query.strip()}")
        return ("?" + "&".join(params)) if params else ""

    def get_stations(self, statuses: Optional[List[str]] = None, country: Optional[str] = None, dj_language: Optional[str] = None, query: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            q = self._build_query(statuses, country, dj_language, query)
            return self.client.get(f"ai/stations{q}")
        except Exception as e:
            self.logger.error(f"Error calling /api/ai/stations: {e}")
            return None

    def get_station_live(self, slug: str) -> Optional[Dict[str, Any]]:
        if not slug or not isinstance(slug, str):
            return None
        try:
            return self.client.get(f"ai/station/{slug}/live")
        except Exception as e:
            self.logger.error(f"Error calling /api/ai/station/{slug}/live: {e}")
            return None
