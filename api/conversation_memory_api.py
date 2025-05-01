from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from typing import List, Union, Optional
from pydantic import Field


class APIBackedConversationMemory(ConversationBufferMemory):
    brand: str = Field(...)
    api_client: Optional[object] = Field(default=None)

    def __init__(self, brand: str, api_client, *args, **kwargs):
        kwargs['brand'] = brand
        kwargs['api_client'] = api_client
        super().__init__(*args, **kwargs)
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
        if not self.messages:
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

        try:
            endpoint = "ai/memory/"
            self.api_client.post(endpoint, payload)
        except Exception:
            pass

    def load_memory(self) -> None:
        response = self.api_client.get(f"ai/memory/{self.brand}")
        if response and 'content' in response:
            if isinstance(response['content'], list):
                self.messages = [
                    HumanMessage(content=msg['text'])
                    if msg['type'] == 'HumanMessage' else AIMessage(content=msg['text'])
                    for msg in response['content']
                ]