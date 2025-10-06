# api/interaction_memory.py

import logging
from typing import Any, Dict, Union

class InteractionMemory:
    def __init__(self, api_client: Any, brand: str):
        self.api_client = api_client
        self.brand = brand
        self.logger = logging.getLogger(__name__)
        self.ai_logger = logging.getLogger('tools.interaction_tools.ai')

    def store_memory(self, memory_type: str, content: Union[str, Dict]) -> bool:
        if memory_type == "CONVERSATION_HISTORY":
            payload = {
                "type": 'SONG_INTRO',
                "title": content.get('title', ''),
                "artist": content.get('artist', ''),
                "content": content.get('content', '')
            }
            #self.ai_logger.info(f"STORING HISTORY for '{payload['title']}' by {payload['artist']}:\n{payload['content']}\n{'#'*80}\n")
            self.api_client.patch(f"ai/memory/history/brand/{self.brand}", data=payload)
            return True
        else:
            return False

    def store_conversation_history(self, content: Union[str, Dict]) -> bool:
        return self.store_memory('CONVERSATION_HISTORY', content)

    def reset_messages(self) -> Dict[str, int]:
        try:
            response = self.api_client.patch(f"ai/memory/reset/{self.brand}/MESSAGE", data={})
            self.ai_logger.info(f"RESET MESSAGES: {response.get('removedCount', 0)} messages removed\n{'~' * 40}\n")
            return response
        except Exception as e:
            self.logger.error(f"Error resetting messages for brand {self.brand}: {e}")
            return {"removedCount": 0}

    def reset_events(self) -> Dict[str, int]:
        try:
            response = self.api_client.patch(f"ai/memory/reset/{self.brand}/EVENT", data={})
            #self.ai_logger.info(f"RESET EVENTS: {response.get('removedCount', 0)} events removed\n{'~' * 40}\n")
            return response
        except Exception as e:
            self.logger.error(f"Error resetting events for brand {self.brand}: {e}")
            return {"removedCount": 0}

    def reset_event_by_id(self, event_id: str) -> Dict[str, int]:
        try:
            response = self.api_client.patch(f"ai/memory/reset/{self.brand}/EVENT?id={event_id}", data={})
            self.ai_logger.info(f"RESET EVENT {event_id}: removed\n{'~'*40}\n")
            return response
        except Exception as e:
            self.logger.error(f"Error resetting event {event_id} for brand {self.brand}: {e}")
            return {"removedCount": 0}

    def reset_message_by_id(self, memory_id: str) -> Dict[str, int]:
        try:
            response = self.api_client.patch(f"ai/memory/reset/{self.brand}/MESSAGE?id={memory_id}", data={})
            self.ai_logger.info(f"RESET MESSAGE {memory_id}: removed\n{'~' * 40}\n")
            return response
        except Exception as e:
            self.logger.error(f"Error resetting message {memory_id} for brand {self.brand}: {e}")
            return {"removedCount": 0}

    def get_all_memory_data(self) -> Dict[str, Any]:
        try:
            response = self.api_client.get(
                f"ai/memory/{self.brand}",
                params={
                    'type': [
                        'LISTENER_CONTEXT',
                        'MESSAGE',
                        'CONVERSATION_HISTORY',
                        'AUDIENCE_CONTEXT',
                        'EVENT'
                    ]
                }
            )

            result = {
                'messages': [],
                'message_ids': [],
                'history': [],
                'listeners': [],
                'environment': [],
                'events': [],
                'event_ids': []
            }

            if isinstance(response, dict):
                events_data = response.get('events', [])
                events_content = []
                event_ids = []

                for event in events_data:
                    if isinstance(event, dict) and 'id' in event and 'content' in event:
                        events_content.append(event['content'])
                        event_ids.append(event['id'])
                    else:
                        events_content.append(event)

                messages_data = response.get('messages', [])
                messages_content = []
                message_ids = []

                for msg in messages_data:
                    if isinstance(msg, dict) and 'id' in msg:
                        messages_content.append(msg)
                        message_ids.append(msg['id'])
                    else:
                        messages_content.append(msg)

                result.update({
                    'messages': messages_content,
                    'message_ids': message_ids,
                    'history': response.get('history', []),
                    'listeners': response.get('listeners', []),
                    'environment': response.get('environment', []),
                    'events': events_content,
                    'event_ids': event_ids
                })

            self.ai_logger.info(f"MEMORY DATA RETRIEVED:\n"
                              f"Messages: {len(result['messages'])}\n"
                              f"History: {len(result['history'])}\n"
                              f"Listeners: {len(result['listeners'])}\n"
                              f"Environment: {len(result['environment'])}\n"
                              f"Events: {len(result['events'])}\n"
                              f"{'+'*40}\n")

            return result

        except Exception as e:
            self.logger.error(f"Error fetching all memory data: {e}")
            return {
                'messages': [],
                'message_ids': [],
                'history': [],
                'listeners': [],
                'environment': [],
                'events': [],
                'event_ids': []
            }