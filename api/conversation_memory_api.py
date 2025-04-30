from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from typing import List, Union, Optional
from pydantic import Field


class APIBackedConversationMemory(ConversationBufferMemory):
    brand: str = Field(...)
    api_client: Optional[object] = Field(default=None)

    def __init__(self, brand: str, api_client, *args, **kwargs):
        # Initialize with brand in kwargs to satisfy Pydantic
        kwargs['brand'] = brand
        kwargs['api_client'] = api_client
        super().__init__(*args, **kwargs)

        # Now set up the chat memory
        self.chat_memory = APIBackedChatMessageHistory(
            brand=brand,
            api_client=api_client
        )


class APIBackedChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, brand: str, api_client):
        super().__init__()
        self.brand = brand
        self.api_client = api_client
        self.messages: List[Union[HumanMessage, AIMessage]] = []
        self.load_memory()

    def add_message(self, message: Union[HumanMessage, AIMessage]) -> None:
        self.messages.append(message)
        self._save_to_api()

    def add_user_message(self, message: str) -> None:
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        self.add_message(AIMessage(content=message))

    def clear(self) -> None:
        self.messages = []
        self._save_to_api()

    def _save_to_api(self) -> None:
        memory_data = {
            'brand': self.brand,
            'history': [
                {'type': type(msg).__name__, 'content': msg.content}
                for msg in self.messages
            ]
        }
        self.api_client.post(f"memory/{self.brand}", memory_data)

    def load_memory(self) -> None:
        response = self.api_client.get(f"ai/memory/{self.brand}")
        if response and 'history' in response:
            self.messages = [
                HumanMessage(content=msg['content']) if msg['type'] == 'HumanMessage'
                else AIMessage(content=msg['content'])
                for msg in response['history']
            ]