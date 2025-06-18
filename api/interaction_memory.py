# api/interaction_memory.py

import json
import logging
from typing import List, Any, Dict, Union
from langchain_core.messages import BaseMessage, AIMessage
import html

class InteractionMemory:
    def __init__(self, api_client: Any, brand: str):
        self.api_client = api_client
        self.brand = brand
        self.logger = logging.getLogger(__name__)

    def get_messages(self, memory_type: str) -> List[BaseMessage]:
        try:
            response_data = self.api_client.get(f"ai/memory/{self.brand}/{memory_type}")
            if not isinstance(response_data, list):
                self.logger.warning(f"Unexpected response format for {memory_type}: {type(response_data)}")
                return []

            processed_messages: List[BaseMessage] = []
            for item in response_data:
                if not isinstance(item, dict):
                    self.logger.warning(f"Skipping non-dict item in {memory_type} memory: {item}")
                    continue

                content_data = item.get('content')
                if isinstance(content_data, dict):
                    json_content_string = json.dumps(content_data)
                    processed_messages.append(AIMessage(content=json_content_string))
                else:
                    self.logger.warning(
                        f"Skipping item with missing/invalid content type for {memory_type}: {type(content_data)}, item: {item}")

            return processed_messages
        except Exception as e:
            self.logger.error(f"Error fetching {memory_type} messages: {str(e)}", exc_info=True)
            return []

    def store_memory(self, memory_type: str, content: Union[str, Dict]) -> bool:
        if memory_type == "CONVERSATION_HISTORY":
            sanitized_title = html.escape(content['title'])
            sanitized_artist = html.escape(content['artist'])
            sanitized_content_text = html.escape(content['content'])  # Assuming 'content' is text

            payload = {
                "type": 'SONG_INTRO',
                "title": sanitized_title,
                "artist": sanitized_artist,
                "content": sanitized_content_text
            }
            self.api_client.patch(f"ai/memory/history/brand/{self.brand}", data=payload)
            return True
        else:
            self.logger.error(f"Memory type '{memory_type}' is not supported by this specialized 'patch' logic.")
            return False

    def get_listeners(self) -> List[BaseMessage]:
        return self.get_messages('LISTENERS')

    def get_audience_context(self) -> List[BaseMessage]:
        return self.get_messages('AUDIENCE_CONTEXT')

    def get_conversation_history(self) -> List[BaseMessage]:
        return self.get_messages('CONVERSATION_HISTORY')

    def store_conversation_history(self, content: Union[str, Dict]) -> bool:
        return self.store_memory('CONVERSATION_HISTORY', content)
