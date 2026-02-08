import logging
from typing import Optional

from api.broadcaster_client import BroadcasterAPIClient
from models.live_container import LiveContainer


class LiveStationsAPI:
    def __init__(self, config):
        self.client = BroadcasterAPIClient(config)
        self.logger = logging.getLogger(__name__)

    async def get_live_radio_stations(self, use_statuses: str | None = None) -> Optional[LiveContainer]:
        try:
            result = await self.client.get(f"ai/live/stations?statuses={use_statuses}")
            if result is None:
                self.logger.warning("No data returned from /api/ai/live/stations")
                return None
            if not isinstance(result, dict):
                self.logger.error(f"Invalid response type from /api/ai/live/stations: {type(result)}, value: {result}")
                return None
            live_container = LiveContainer.from_dict(result)
            if len(live_container) > 0:
                self.logger.info(f"Retrieved {len(live_container)} stream from broadcaster")
            return live_container
        except Exception as e:
            self.logger.error(f"Error calling /api/ai/live/stations: {e}")
            return None
