from typing import List
from typing import Sequence, Any, Dict

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage

from api.broadcaster_client import BroadcasterAPIClient


def _format_message_for_payload(message: BaseMessage, brand: str) -> Dict[str, Any] | None:
    if not isinstance(message.content, str):
        return None

    payload_message_type: str = message.type.upper()

    return {
        "brand": brand,
        "messageType": payload_message_type,
        "content": {
            "description": message.content
        }
    }


class InteractionMemory(BaseChatMessageHistory):
    def __init__(self, brand: str, api_client: BroadcasterAPIClient):
        self.brand = brand,
        self.api_client = api_client

    def get_messages(self, memory_type: str) -> List[BaseMessage]:
        response: Any = self.api_client.get(f"ai/memory/{self.brand}/{memory_type}")
        if not isinstance(response, list):
            return []

        processed_messages: List[BaseMessage] = []
        for item in response:
            if not isinstance(item, dict):
                continue
            message_type: str | None = item.get('messageType')
            content_data: Dict[str, Any] | None = item.get('content')

            if isinstance(content_data, dict) and 'description' in content_data:
                message_text: str = content_data['description']
                if message_type in ['CONVERSATION_HISTORY']:
                    processed_messages.append(AIMessage(content=message_text))

        return processed_messages

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        existing_messages: List[BaseMessage] = self.get_messages('CONVERSATION_HISTORY')
        all_messages: List[BaseMessage] = list(existing_messages)
        all_messages.extend(messages)

        payload_list: List[Dict[str, Any]] = [
            formatted for msg in all_messages if (formatted := _format_message_for_payload(msg, self.brand)) is not None
        ]

        if not payload_list:
            return

        try:
            response = self.api_client.post(
                f"ai/memory/{self.brand}",
                data=payload_list
            )
            response.raise_for_status()
        except Exception:
            pass

    def clear(self) -> None:
        try:
            response: Any = self.api_client.delete(f"ai/memory/{self.brand}")
            response.raise_for_status()
        except Exception:
            pass
