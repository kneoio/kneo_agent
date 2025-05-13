from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from typing import List, Union, Optional, Dict, Any
from pydantic import Field, PrivateAttr

from api.broadcaster_client import BroadcasterAPIClient


class APIBackedConversationMemory(ConversationBufferMemory):
    brand: str = Field(...)
    _api_client: BroadcasterAPIClient = PrivateAttr()

    def __init__(self, brand: str, config: Dict[str, Any], **kwargs):
        api_client = BroadcasterAPIClient(config)
        chat_memory = APIBackedChatMessageHistory(
            brand=brand,
            api_client=api_client
        )
        super().__init__(
            brand=brand,
            chat_memory=chat_memory,
            **kwargs
        )
        self._api_client = api_client
        print(f"Initialized memory for brand: {brand}")  # Print initialization


class APIBackedChatMessageHistory(BaseChatMessageHistory):
    def __init__(
            self,
            brand: str,
            api_client: BroadcasterAPIClient,
            **kwargs
    ):
        super().__init__(**kwargs)
        self.brand = brand
        self.api_client = api_client
        self.messages: List[Union[HumanMessage, AIMessage]] = []
        self.load_memory()
        print(f"Loaded existing messages: {len(self.messages)}")  # Print loaded messages

    def add_message(self, message: Union[HumanMessage, AIMessage]) -> None:
        self.messages.append(message)
        print(f"Added message: {message}")  # Print added message
        self._save_to_api()

    def add_user_message(self, message: str) -> None:
        print(f"Adding user message: {message}")  # Print user message
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        print(f"Adding AI message: {message}")  # Print AI message
        self.add_message(AIMessage(content=message))

    def clear(self) -> None:
        print("Clearing all messages")  # Print clear action
        self.messages = []
        self._save_to_api()

    def _save_to_api(self) -> None:
        if not self.messages:
            print("No messages to save")  # Print if empty
            return

        last_message = self.messages[-1]
        payload = {
            'brand': self.brand,
            'messageType': type(last_message).__name__,
            'content': {
                'text': last_message.content,
                'type': type(last_message).__name__
            }
        }
        print(f"Saving to API: {payload}")  # Print API payload

        try:
            response = self.api_client.post("ai/memory/", payload)
            print(f"API Response: {response}")  # Print API response
        except Exception as e:
            print(f"API Error: {e}")  # Print errors

    def load_memory(self) -> None:
        response = self.api_client.get(f"ai/memory/{self.brand}")
        print(f"API Load Response: {response}")  # Print API load response
        if response and 'content' in response:
            self.messages = [
                HumanMessage(content=msg['text'])
                if msg['type'] == 'HumanMessage'
                else AIMessage(content=msg['text'])
                for msg in response.get('content', [])
            ]
            print(f"Loaded {len(self.messages)} messages")  # Print loaded count