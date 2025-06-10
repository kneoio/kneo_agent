import json
import logging
from typing import List, Any
from langchain_core.messages import BaseMessage, AIMessage


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
                elif isinstance(content_data, str):
                    processed_messages.append(AIMessage(content=content_data))
                else:
                    self.logger.warning(f"Skipping item with missing/invalid content type for {memory_type}: {type(content_data)}, item: {item}")
            return processed_messages
        except Exception as e:
            self.logger.error(f"Error fetching {memory_type} messages: {str(e)}", exc_info=True)
            return []

    def get_listeners(self) -> List[BaseMessage]:
        return self.get_messages('LISTENERS')

    def get_audience_context(self) -> List[BaseMessage]:
        return self.get_messages('AUDIENCE_CONTEXT')

    def get_conversation_history(self) -> List[BaseMessage]:
        return self.get_messages('CONVERSATION_HISTORY')