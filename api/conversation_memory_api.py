from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain.memory.chat_message_histories import BaseChatMessageHistory
from typing import List, Union


class APIBackedConversationMemory(ConversationBufferMemory):
    def __init__(self, brand: str, api_client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brand = brand
        self.api_client = api_client
        # Replace with our properly typed implementation
        self.chat_memory = APIBackedChatMessageHistory(
            brand=brand,
            api_client=api_client
        )


class APIBackedChatMessageHistory(BaseChatMessageHistory):  # Now properly inherits
    def __init__(self, brand: str, api_client):
        super().__init__()
        self.brand = brand
        self.api_client = api_client
        self.messages: List[Union[HumanMessage, AIMessage]] = []
        self.load_memory()

    def add_message(self, message: Union[HumanMessage, AIMessage]) -> None:
        """Add a message to the store"""
        self.messages.append(message)
        self._save_to_api()

    def add_user_message(self, message: str) -> None:
        """Add a user message to the store"""
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        """Add an AI message to the store"""
        self.add_message(AIMessage(content=message))

    def clear(self) -> None:
        """Clear all messages"""
        self.messages = []
        self._save_to_api()

    def _save_to_api(self) -> None:
        """Internal save method"""
        memory_data = {
            'brand': self.brand,
            'history': [
                {'type': type(msg).__name__, 'content': msg.content}
                for msg in self.messages
            ]
        }
        self.api_client.post(f"memory/{self.brand}", memory_data)

    def load_memory(self) -> None:
        """Load from API"""
        response = self.api_client.get(f"memory/{self.brand}")
        if response and 'history' in response:
            self.messages = [
                HumanMessage(content=msg['content']) if msg['type'] == 'HumanMessage'
                else AIMessage(content=msg['content'])
                for msg in response['history']
            ]