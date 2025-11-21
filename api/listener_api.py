import logging
from typing import Optional

from api.broadcaster_client import BroadcasterAPIClient
from models.listener import Listener


class ListenerAPI:
    def __init__(self, config):
        self.client = BroadcasterAPIClient(config)
        self.logger = logging.getLogger(__name__)

    async def get_listener_by_telegram_name(self, telegram_name: str) -> Optional[Listener]:
        try:
            result = self.client.get(f"ai/listener/by-telegram-name/{telegram_name}")
            if not result:
                self.logger.info(f"No listener found for telegram name: {telegram_name}")
                return None
            listener = Listener.from_dict(result)
            self.logger.info(f"Retrieved listener: {listener.slugName} (telegram: {telegram_name})")
            return listener
        except Exception as e:
            self.logger.error(f"Error calling /api/ai/listener/by-telegram-name/{telegram_name}: {e}")
            return None
