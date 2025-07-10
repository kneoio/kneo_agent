# api/interaction_memory.py

import logging
from typing import List, Any, Dict, Union
from langchain_core.messages import BaseMessage, AIMessage
from models.memory_payload import MemoryPayload

class InteractionMemory:
    def __init__(self, api_client: Any, brand: str):
        self.api_client = api_client
        self.brand = brand
        self.logger = logging.getLogger(__name__)

    def get_messages(self, memory_type: str) -> Union[List[BaseMessage], str]:
        response_data = self.api_client.get(f"ai/memory/{self.brand}/{memory_type}")
        
        processed_messages: List[BaseMessage] = []
        for item in response_data:
            memory_payload = MemoryPayload(item)
            if memory_payload.is_valid():
                json_content_string = memory_payload.get_content_as_json()
                processed_messages.append(AIMessage(content=json_content_string))

        if memory_type == "CONVERSATION_HISTORY" and processed_messages:
            return processed_messages[0].content
        
        return processed_messages

    def store_memory(self, memory_type: str, content: Union[str, Dict]) -> bool:
        if memory_type == "CONVERSATION_HISTORY":
            payload = {
                "type": 'SONG_INTRO',
                "title": content.get('title', ''),
                "artist": content.get('artist', ''),
                "content": content.get('content', '')
            }
            self.api_client.patch(f"ai/memory/history/brand/{self.brand}", data=payload)
            return True
        else:
            return False

    def get_listeners(self) -> List[BaseMessage]:
        return self.get_messages('LISTENER_CONTEXTS')

    def get_audience_context(self) -> List[BaseMessage]:
        return self.get_messages('AUDIENCE_CONTEXT')

    def get_conversation_history(self) -> str:
        return self.get_messages('CONVERSATION_HISTORY')

    def store_conversation_history(self, content: Union[str, Dict]) -> bool:
        return self.store_memory('CONVERSATION_HISTORY', content)

    def get_all_memory_data(self) -> Dict[str, Any]:
        """
        Fetches all memory data in a single request.
        Returns a dictionary with the structure:
        {
            'message': Dict,
            'introductions': List[Dict],
            'listeners': List[Dict],
            'environment': List[Dict]
        }
        """
        try:
            response = self.api_client.get(
                f"ai/memory/{self.brand}",
                params={
                    'type': [
                        'LISTENER_CONTEXTS',
                        'INSTANT_MESSAGE',
                        'CONVERSATION_HISTORY',
                        'AUDIENCE_CONTEXT'
                    ]
                }
            )
            
            # Initialize default structure in case some fields are missing
            result = {
                'message': {},
                'introductions': [],
                'listeners': [],
                'environment': []
            }
            
            # Update with actual data from response
            if isinstance(response, dict):
                result.update({
                    'message': response.get('message', {}),
                    'introductions': response.get('introductions', []),
                    'listeners': response.get('listeners', []),
                    'environment': response.get('environment', [])
                })
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching all memory data: {e}")
            # Return empty structure on error
            return {
                'message': {},
                'introductions': [],
                'listeners': [],
                'environment': []
            }