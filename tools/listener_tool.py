import logging
from typing import Dict, Any, Optional
from api.listener_api import ListenerAPI

logger = logging.getLogger(__name__)

_listener_api: Optional[ListenerAPI] = None


def set_listener_api(api: ListenerAPI) -> None:
    global _listener_api
    _listener_api = api


async def get_listener_by_telegram(telegram_name: str) -> Dict[str, Any]:
    if not _listener_api:
        logger.error("ListenerAPI not initialized")
        return {"error": "ListenerAPI not available"}
    api = _listener_api
    listener = await api.get_listener_by_telegram_name(telegram_name)
    
    if not listener:
        return {"found": False, "telegram_name": telegram_name}
    
    return {
        "found": True,
        "id": listener.id,
        "telegram_name": listener.telegramName,
        "nick_name": listener.nickName.get("en", listener.slugName),
        "slug_name": listener.slugName,
        "country": listener.country,
        "listener_of": listener.listenerOf
    }


def get_tool_definition() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "get_listener_by_telegram",
            "description": "Look up a listener by their Telegram username to recognize returning users and personalize greetings",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_name": {
                        "type": "string",
                        "description": "The Telegram username to look up"
                    }
                },
                "required": ["telegram_name"]
            }
        }
    }
