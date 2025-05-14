from langchain.memory import ConversationBufferMemory, __all__
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from typing import List, Union, Optional, Dict, Any
from pydantic import Field, PrivateAttr
import requests
from langchain_core.messages import AIMessage
from langchain_core.chat_history import BaseChatMessageHistory

from api.broadcaster_client import BroadcasterAPIClient


class ConversationMemoryAPI:
    def __init__(self, brand: str, api_client: BroadcasterAPIClient):
        self.brand = brand,
        self.api_client = api_client

    def save_history_to_api(self, current_history: BaseChatMessageHistory):
        all_messages = current_history.messages
        serialized_messages = [msg.dict() for msg in all_messages]
        history = BaseChatMessageHistory()
        data_to_save = {
            "messages": serialized_messages
        }

        payload = {
            'brand': self.brand,
            'messageType': 'CONVERSATION_HISTORY',
            'content': {
                'text': current_history,
            }
        }
        print(f"Saving to API: {payload}")

        try:
            response = self.api_client.post("ai/memory/", payload)
            print(f"API Response: {response}")
        except Exception as e:
            print(f"API Error: {e}")

        try:
            response = requests.post(api_url, json=data_to_save)
            response.raise_for_status()
            print(f"History saved successfully for session {session_id}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while saving history for session {session_id}: {e}")

        dj_utterance_1 = "Now, spinning up some classic rock for you!"
        new_message_1 = AIMessage(content=dj_utterance_1)

        history.add_message(new_message_1)

        save_history_to_api(history, session_id, api_url)


#def load_memory(self) -> None:

#    response = self.api_client.get(f"ai/memory/{self.brand}")
#    print(f"API Load Response: {response}")  # Print API load response
#    if response and 'content' in response:
#        self.messages = [
#            HumanMessage(content=msg['text'])
#            if msg['type'] == 'HumanMessage'
#            else AIMessage(content=msg['text'])
#            for msg in response.get('content', [])
#        ]
#        print(f"Loaded {len(self.messages)} messages")  # Print loaded count